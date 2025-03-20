# test_plot_updates.py
import pytest
import numpy as np
from ui import SensorPlotter

def test_update_plot_ui(sensor_plotter):
    """
    Test that after new sensor data is handled, the plot and statistics update.
    """
    # Let n be the number of sensors.
    n = len(sensor_plotter.sensor_config)
    
    # Simulate a reading event with one timestamp.
    sensor_plotter.timestamps = [1]
    sensor_plotter.sensor_data = [[40] for _ in range(n)]
    sensor_plotter.full_timestamps = [1]
    sensor_plotter.full_sensor_data = [[40] for _ in range(n)]
    
    # Reinitialize plot lines; this clears sensor_data and timestamps.
    sensor_plotter.reinitialize_plot_lines()
    
    # Now simulate new data. Provide new_values with a value for each sensor.
    new_values = [50] * n
    sensor_plotter.handle_new_data(new_values, 2)
    
    # Verify that the plot lines have been updated.
    assert len(sensor_plotter.lines) == n, "Plot lines count does not match sensor configuration."
    x_data, y_data = sensor_plotter.lines[0].get_data()
    assert len(x_data) > 0, "No x data in plot line."
    # The last value in the y_data of the first sensor should be 50.
    assert y_data[-1] == 50, "Plot line did not update with the new sensor value."
