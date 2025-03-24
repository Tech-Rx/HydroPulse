import pytest
from PyQt5 import QtWidgets, QtCore
from ui import SensorPlotter
from sensor import Sensor
from config import ADC_MAX, VOLTAGE_FULL_SCALE, POLL_INTERVAL_MS


# --- Fake Modbus Client for Integration Testing ---
class FakeModbusClient:
    def __init__(self, *args, **kwargs):
        self.connected = False

    def connect(self):
        self.connected = True
        return True

    def close(self):
        self.connected = False


# --- Fixtures ---
@pytest.fixture
def fake_modbus_client():
    return FakeModbusClient()


@pytest.fixture
def sensor_plotter(qtbot):
    """
    Fixture to create and return a SensorPlotter instance.
    """
    window = SensorPlotter()
    qtbot.addWidget(window)
    return window


# --- Integration Test for Starting and Stopping Modbus ---
@pytest.mark.gui  # Add this marker
def test_modbus_start_and_stop(qtbot, sensor_plotter, monkeypatch):
    """
    Test that starting Modbus updates the status and creates a Sensor instance and QTimer,
    and that stopping Modbus updates the status and cleans up the sensor and timer.
    """
    # Replace the modbus_client with our fake one.
    monkeypatch.setattr("ui.ModbusClient", FakeModbusClient)

    # Start modbus connection.
    sensor_plotter.start_modbus()

    # Check that the status label shows "Connected".
    assert "Connected" in sensor_plotter.status_label.text()
    # Check that the Sensor instance and sensor_timer have been created.
    assert sensor_plotter.sensor is not None, "Expected sensor instance to be created."
    assert (
        hasattr(sensor_plotter, "sensor_worker")
        and sensor_plotter.sensor_worker is not None
    ), "Expected sensor worker to be started."

    # Now, stop the modbus connection.
    sensor_plotter.stop_modbus()

    # Verify cleanup.
    assert (
        sensor_plotter.sensor is None
    ), "Expected sensor instance to be None after stopping."
    assert not (
        hasattr(sensor_plotter, "sensor_worker") and sensor_plotter.sensor_worker
    ), "Expected sensor worker to be None after stopping."
    status_text = sensor_plotter.status_label.text()
    assert "Disconnected" in status_text or "Connection stopped" in status_text


# The other tests (e.g., test_save_data_no_timestamps and test_status_line_reset) can remain unchanged.
