# test_plot_statistics.py
import pytest
import numpy as np
from ui import SensorPlotter

@pytest.mark.gui
def test_plot_and_statistics_updates(sensor_plotter):
    """
    Simulate a sequence of sensor updates and verify that:
      - The plot lines are updated with a rolling window of data.
      - The statistics panel shows the correct current, min, max, and avg values.
    """
    n = len(sensor_plotter.sensor_config)
    # Set initial timestamp and data for each sensor.
    # For simplicity, we simulate 5 readings over 5 seconds.
    sensor_plotter.timestamps = [1, 2, 3, 4, 5]
    sensor_plotter.sensor_data = [[10, 20, 30, 40, 50] for _ in range(n)]
    sensor_plotter.full_timestamps = sensor_plotter.timestamps.copy()
    sensor_plotter.full_sensor_data = [
        data.copy() for data in sensor_plotter.sensor_data
    ]

    # Call update_plot_ui to refresh the plot based on current data.
    sensor_plotter.update_plot_ui()

    # For the first sensor, check that the x data is non-decreasing and last y value equals 50.
    x_data, y_data = sensor_plotter.lines[0].get_data()
    assert len(x_data) > 0, "Plot line x data is empty."
    assert np.all(np.diff(x_data) >= 0), "Plot line x data is not non-decreasing."
    assert y_data[-1] == 50, "Plot line did not update with the expected sensor value."

    # Check that statistics labels (if any) are updated.
    for sensor in sensor_plotter.sensor_config:
        labels = sensor_plotter.sensor_stats_labels.get(sensor["name"])
        assert (
            labels is not None
        ), f"No stats labels found for sensor '{sensor['name']}'."
        # In our simulated data, current value should be 50, min 10, max 50, and avg 30.
        assert (
            "50" in labels["current"].text()
        ), f"Expected current value '50' for {sensor['name']}."
        assert (
            "10" in labels["min"].text()
        ), f"Expected min value '10' for {sensor['name']}."
        assert (
            "50" in labels["max"].text()
        ), f"Expected max value '50' for {sensor['name']}."
        assert (
            "30" in labels["avg"].text()
        ), f"Expected avg value '30' for {sensor['name']}."
