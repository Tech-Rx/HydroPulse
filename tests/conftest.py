import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "hydro_pulse")))

import pytest
from PyQt5 import QtWidgets, QtCore
from ui import SensorPlotter
from PyQt5.QtCore import QThreadPool

# Session-scoped QApplication fixture to ensure a single instance across tests.
@pytest.fixture(scope="session", autouse=True)
def qt_app():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    yield app
    app.quit()

# Disable background tasks that use QThreadPool.
@pytest.fixture(autouse=True)
def disable_background_tasks(monkeypatch):
    monkeypatch.setattr(QThreadPool.globalInstance(), "start", lambda task: None)

# Disable file saving during tests to avoid blocking I/O.
@pytest.fixture(autouse=True)
def disable_file_saving(monkeypatch):
    from ui import SensorPlotter
    monkeypatch.setattr(SensorPlotter, "save_data", lambda self: None)
    monkeypatch.setattr(SensorPlotter, "save_full_session_data", lambda self: None)

# Dummy worker for sensor data simulation.
class DummySensorWorker(QtCore.QObject):
    data_ready = QtCore.pyqtSignal(list, float)
    _running = False  # Added _running attribute

    def start(self):
        self._running = True

    def stop(self):
        self._running = False

# New closeEvent override that mimics cleanup but without triggering file-saving tasks.
@pytest.fixture(autouse=True)
def disable_close_event(monkeypatch):
    def dummy_close_event(self, event):
        # Stop and clear sensor_worker.
        if hasattr(self, "sensor_worker") and self.sensor_worker is not None:
            try:
                self.sensor_worker.stop()
            except Exception:
                pass
            self.sensor_worker = None
        # Stop and clear sensor_timer.
        if hasattr(self, "sensor_timer") and self.sensor_timer is not None:
            try:
                self.sensor_timer.stop()
            except Exception:
                pass
            self.sensor_timer = None
        # Clear sensor and modbus_client references.
        self.sensor = None
        self.modbus_client = None
        event.accept()
    monkeypatch.setattr(SensorPlotter, "closeEvent", dummy_close_event)

# Fixture providing a SensorPlotter instance with dummy worker.
@pytest.fixture
def sensor_plotter(qtbot):
    window = SensorPlotter()
    qtbot.addWidget(window)
    window.sensor_worker = DummySensorWorker()
    yield window
    # Ensure any timers are stopped.
    if hasattr(window, "com_port_timer") and window.com_port_timer is not None:
        window.com_port_timer.stop()
        window.com_port_timer = None
    window.close()
    QtWidgets.QApplication.processEvents()

# Fixture for hardware simulator if needed.
class DummyHardwareSimulator:
    def __init__(self, plotter):
        self.plotter = plotter

    def trigger_disconnect(self):
        self.plotter.stop_modbus()
        print("Simulated disconnect triggered")

@pytest.fixture
def hardware_simulator(sensor_plotter):
    yield DummyHardwareSimulator(sensor_plotter)

# Wait for any pending QThreadPool tasks at session end.
@pytest.fixture(scope="session", autouse=True)
def wait_for_threadpool():
    yield
    QThreadPool.globalInstance().waitForDone(1000)
