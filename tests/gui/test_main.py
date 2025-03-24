import sys
import pytest
from PyQt5 import QtWidgets
from ui import SensorPlotter

@pytest.mark.gui
def test_sensor_plotter_instantiation(qtbot):
    """
    Test that the SensorPlotter window can be instantiated without errors.
    This test does not start the full event loop.
    """
    # Instantiate the main window.
    window = SensorPlotter()
    # qtbot.addWidget ensures the widget is properly tracked by pytest-qt.
    qtbot.addWidget(window)
    # Verify that window is indeed an instance of SensorPlotter.
    assert isinstance(window, SensorPlotter)
