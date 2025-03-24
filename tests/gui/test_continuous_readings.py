# test_continuous_readings.py
import pytest
from ui import SensorPlotter
from sensor import Sensor
from config import POLL_INTERVAL_MS


# Dummy response and client classes.
class DummyResponse:
    def __init__(self, registers):
        self.registers = registers

    def isError(self):
        return False


class DummyModbusClient:
    def read_holding_registers(self, address, count, slave):
        return DummyResponse([2048])

    def connect(self):
        return True

    def close(self):
        pass


@pytest.fixture
def dummy_sensor():
    # Create a dummy sensor with one sensor configuration.
    sensor_config = [
        {
            "channel": 1,
            "scale": 600,
            "offset": 2,
            "calibration": 1,
            "name": "Test Sensor",
            "color": "red",
            "style": "-",
        }
    ]
    client = DummyModbusClient()
    sensor = Sensor(sensor_config, client)
    return sensor

@pytest.mark.gui  # Add this marker
def test_continuous_sensor_readings(sensor_plotter, dummy_sensor, qtbot):
    """
    Simulate continuous sensor reading by manually calling read_sensor_data()
    multiple times, and verify that handle_new_data updates the UI data arrays.
    """
    # Set the SensorPlotter's sensor to our dummy sensor.
    sensor_plotter.sensor = dummy_sensor

    # Synchronize the sensor configuration with that of dummy_sensor.
    sensor_plotter.sensor_config = dummy_sensor.sensor_config

    # Reinitialize plot lines to rebuild self.lines and reset sensor_data.
    sensor_plotter.reinitialize_plot_lines()

    # Check that sensor_data now has one list per sensor.
    n = len(sensor_plotter.sensor_config)
    assert (
        len(sensor_plotter.sensor_data) == n
    ), "sensor_data length does not match sensor_config."

    # Clear any existing timestamps.
    sensor_plotter.timestamps = []

    # Call read_sensor_data() several times to simulate periodic updates.
    for _ in range(3):
        sensor_plotter.read_sensor_data()
        qtbot.wait(POLL_INTERVAL_MS + 50)

    # Verify that timestamps have been updated.
    assert len(sensor_plotter.timestamps) >= 3, "Expected at least 3 timestamps."

    # Verify that each sensor's data list has at least 3 readings.
    for data in sensor_plotter.sensor_data:
        assert len(data) >= 3, "Expected at least 3 sensor readings in each data list."
