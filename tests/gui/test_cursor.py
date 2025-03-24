# test_cursor.py
import pytest
from ui import SensorPlotter

@pytest.mark.gui  # Add this marker
def test_add_cursor(sensor_plotter):
    """
    Test that after calling add_cursor(), the SensorPlotter has a valid cursor attribute.
    """
    sensor_plotter.add_cursor()
    assert hasattr(
        sensor_plotter, "cursor"
    ), "SensorPlotter does not have a 'cursor' attribute after add_cursor()."
    assert (
        sensor_plotter.cursor is not None
    ), "SensorPlotter.cursor is None after add_cursor()."
