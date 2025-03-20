# conftest.py
import pytest
from ui import SensorPlotter

@pytest.fixture
def sensor_plotter(qtbot):
    """
    Fixture to create and return a SensorPlotter instance.
    """
    window = SensorPlotter()
    qtbot.addWidget(window)
    return window
