# test_stress.py
import pytest
import random
from ui import SensorPlotter
from sensor import Sensor
from config import POLL_INTERVAL_MS, ADC_MAX
import numpy as np


# Define a dummy response for stress testing.
class StressDummyResponse:
    def __init__(self, registers):
        self.registers = registers

    def isError(self):
        return False


# Define a dummy modbus client that returns a random reading between 0 and ADC_MAX.
class StressDummyModbusClient:
    def read_holding_registers(self, address, count, slave):
        # Generate a random integer between 0 and ADC_MAX.
        value = random.randint(0, ADC_MAX)
        return StressDummyResponse([value])

    def connect(self):
        return True

    def close(self):
        pass


@pytest.fixture
def stress_dummy_sensor():
    """
    Create a dummy sensor with one sensor configuration for stress testing.
    """
    sensor_config = [
        {
            "channel": 1,
            "scale": 600,
            "offset": 2,
            "calibration": 1,
            "name": "Stress Sensor",
            "color": "green",
            "style": "-",
        }
    ]
    client = StressDummyModbusClient()
    return Sensor(sensor_config, client)

@pytest.mark.gui
def test_stress_sensor_readings(sensor_plotter, stress_dummy_sensor):
    """
    Stress test: simulate a high number of sensor reading cycles and verify that the sensor_data
    and timestamps arrays are updated correctly.
    """
    # Set the SensorPlotter's sensor and synchronize its configuration.
    sensor_plotter.sensor = stress_dummy_sensor
    sensor_plotter.sensor_config = stress_dummy_sensor.sensor_config

    n = len(sensor_plotter.sensor_config)
    sensor_plotter.sensor_data = [[] for _ in range(n)]
    sensor_plotter.full_sensor_data = [[] for _ in range(n)]
    sensor_plotter.timestamps = []
    sensor_plotter.full_timestamps = []

    # Reinitialize plot lines to ensure consistency with the new configuration.
    sensor_plotter.initialize_plot_lines()

    iterations = 1000  # simulate 1000 sensor reading cycles
    for _ in range(iterations):
        sensor_plotter.read_sensor_data()

    # Assert that the number of timestamps equals the number of iterations.
    assert (
        len(sensor_plotter.timestamps) == iterations
    ), "Timestamps count does not match iterations."
    # Assert that each sensor's data list has the same number of readings.
    for data in sensor_plotter.sensor_data:
        assert (
            len(data) == iterations
        ), "Sensor readings count does not match iterations."

@pytest.mark.gui
def test_stress_update_plot(sensor_plotter, stress_dummy_sensor):
    """
    Stress test: simulate a high number of sensor readings and then update the plot.
    Verify that update_plot_ui() processes a large rolling window without errors.
    """
    sensor_plotter.sensor = stress_dummy_sensor
    sensor_plotter.sensor_config = stress_dummy_sensor.sensor_config
    sensor_plotter.initialize_plot_lines()

    n = len(sensor_plotter.sensor_config)
    sensor_plotter.sensor_data = [[] for _ in range(n)]
    sensor_plotter.timestamps = []

    iterations = 1000  # simulate 1000 sensor reading cycles
    for _ in range(iterations):
        sensor_plotter.read_sensor_data()

    # After 1000 readings, update the plot.
    sensor_plotter.update_plot_ui()

    # Check that the first plot line has x and y data.
    x_data, y_data = sensor_plotter.lines[0].get_data()
    assert len(x_data) > 0, "Plot update did not produce any x data."
    # Optionally, check that y_data has the expected number of points.
    assert len(y_data) > 0, "Plot update did not produce any y data."
