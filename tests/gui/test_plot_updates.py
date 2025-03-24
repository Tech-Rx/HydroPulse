import pytest
import numpy as np
from ui import SensorPlotter

# Dummy line that simply stores data.
class DummyLine:
    def __init__(self):
        self._x = []
        self._y = []
    def set_data(self, x, y):
        self._x = x
        self._y = y
    def get_data(self):
        return self._x, self._y

# Dummy Axes and Canvas to avoid any backend drawing calls.
class DummyAx:
    def clear(self):
        pass
    def set_title(self, title):
        pass
    def set_xlabel(self, label):
        pass
    def set_ylabel(self, label):
        pass
    def set_ylim(self, bottom, top):
        pass
    def set_xlim(self, left, right):
        pass
    def grid(self, flag):
        pass
    def set_yticks(self, ticks):
        pass
    def set_xticks(self, ticks):
        pass

class DummyCanvas:
    def __init__(self):
        self.ax = DummyAx()
    def draw(self):
        pass

@pytest.mark.gui
def test_update_plot_ui(sensor_plotter, monkeypatch):
    """
    Test that after new sensor data is handled, the plot and statistics update.
    This version replaces real canvas and plot lines with dummy objects to avoid segfaults.
    """
    # Force Matplotlib to use the Agg backend.
    monkeypatch.setenv("MPLBACKEND", "Agg")
    
    # Replace the canvas with a dummy canvas.
    dummy_canvas = DummyCanvas()
    monkeypatch.setattr(sensor_plotter, "canvas", dummy_canvas)
    
    # Override setup_plot_axes to do nothing.
    monkeypatch.setattr(sensor_plotter, "setup_plot_axes", lambda: None)
    
    # Override initialize_plot_lines to create dummy lines.
    def dummy_initialize_plot_lines():
        n = len(sensor_plotter.sensor_config)
        sensor_plotter.lines = [DummyLine() for _ in range(n)]
    monkeypatch.setattr(sensor_plotter, "initialize_plot_lines", dummy_initialize_plot_lines)
    
    # Disable add_cursor.
    monkeypatch.setattr(sensor_plotter, "add_cursor", lambda: None)
    
    # Simulate initial sensor data.
    n = len(sensor_plotter.sensor_config)
    sensor_plotter.timestamps = [1]
    sensor_plotter.sensor_data = [[40] for _ in range(n)]
    sensor_plotter.full_timestamps = [1]
    sensor_plotter.full_sensor_data = [[40] for _ in range(n)]
    
    # Call reinitialize_plot_lines (which now creates dummy lines).
    sensor_plotter.reinitialize_plot_lines()
    
    # Simulate new sensor data.
    new_values = [50] * n
    sensor_plotter.handle_new_data(new_values, 2)
    
    # Verify that dummy plot lines have been updated.
    assert len(sensor_plotter.lines) == n, "Plot lines count does not match sensor configuration."
    x_data, y_data = sensor_plotter.lines[0].get_data()
    assert len(x_data) > 0, "No x data in plot line."
    assert y_data[-1] == 50, "Plot line did not update with the new sensor value."
