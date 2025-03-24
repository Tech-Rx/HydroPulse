# test_ui_close_event.py
import pytest
from PyQt5.QtGui import QCloseEvent
from ui import SensorPlotter


class DummyTimer:
    def stop(self):
        pass

@pytest.mark.gui
def test_close_event_cleans_up(sensor_plotter):
    """
    Test that closeEvent properly cleans up sensor, sensor_timer, and modbus_client.
    """
    # Assign dummy objects that support the expected behavior.
    sensor_plotter.sensor = object()  # dummy sensor object
    sensor_plotter.sensor_timer = DummyTimer()  # dummy timer with a stop() method
    sensor_plotter.modbus_client = object()

    # To simulate a working sensor_worker, we can also add a dummy with a stop() method.
    class DummyWorker:
        def stop(self):
            pass

    sensor_plotter.sensor_worker = DummyWorker()

    event = QCloseEvent()
    sensor_plotter.closeEvent(event)

    assert (
        sensor_plotter.sensor_worker is None
    ), "Sensor worker was not cleared on close."
    assert sensor_plotter.sensor is None, "Sensor was not cleared on close."
    assert sensor_plotter.sensor_timer is None, "Sensor timer was not cleared on close."
    assert (
        sensor_plotter.modbus_client is None
    ), "Modbus client was not cleared on close."
