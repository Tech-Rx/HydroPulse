import time
import pytest
from PyQt5 import QtWidgets, QtCore
from ui import SensorPlotter

@pytest.mark.gui
def test_ui_update_plot_ui(qtbot):
    """
    Simulate sensor data updates and verify that the statistics panel reflects the correct values.
    """
    window = SensorPlotter()
    qtbot.addWidget(window)

    # Ensure that there's at least one sensor in the configuration.
    if not window.sensor_config:
        pytest.skip("No sensor configured.")

    # Simulate 10 sensor readings:
    now = time.time()
    window.timestamps = [now + i for i in range(10)]
    # For each sensor in the configuration, simulate 10 readings of 300.
    window.sensor_data = [[300] * 10 for _ in window.sensor_config]

    # Call update_plot_ui() to update the plot and statistics panel.
    window.update_plot_ui()

    # Verify that the statistics labels for each sensor show the expected value.
    # We expect current, min, max, and average to be "300.00".
    for sensor in window.sensor_config:
        labels = window.sensor_stats_labels.get(sensor["name"])
        assert (
            labels is not None
        ), f"Statistics labels missing for sensor {sensor['name']}"
        assert (
            labels["current"].text() == "300.00"
        ), f"Expected current value 300.00, got {labels['current'].text()}"
        assert (
            labels["min"].text() == "300.00"
        ), f"Expected min value 300.00, got {labels['min'].text()}"
        assert (
            labels["max"].text() == "300.00"
        ), f"Expected max value 300.00, got {labels['max'].text()}"
        assert (
            labels["avg"].text() == "300.00"
        ), f"Expected avg value 300.00, got {labels['avg'].text()}"

@pytest.mark.gui
def test_ui_reinitialize_plot_lines(qtbot):
    """
    Test that calling reinitialize_plot_lines() clears the sensor data and timestamps.
    """
    window = SensorPlotter()
    qtbot.addWidget(window)

    # Simulate some existing sensor data.
    window.sensor_data = [[300, 310] for _ in window.sensor_config]
    window.timestamps = [time.time(), time.time() + 1]

    # Call reinitialize_plot_lines() which should clear dynamic data.
    window.reinitialize_plot_lines()

    # Verify that sensor_data and timestamps have been reset.
    for data in window.sensor_data:
        assert len(data) == 0, "Sensor data was not reset."
    assert len(window.timestamps) == 0, "Timestamps were not reset."

@pytest.mark.gui
def test_status_line_update(qtbot):
    """Verify status line auto-resets after delay"""
    window = SensorPlotter()
    qtbot.addWidget(window)
    
    # Initial state check
    assert "Ready" in window.status_label.text()
    
    # Set temporary state
    window.update_status_line("Connecting", reset_after=100)
    assert "Connecting" in window.status_label.text()
    
    # Wait for reset using QtBot's event processing
    qtbot.waitUntil(
        lambda: "Ready" in window.status_label.text(),
        timeout=500  # 500ms = 100ms delay + 400ms buffer
    )