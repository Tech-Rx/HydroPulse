import pytest
from PyQt5.QtWidgets import QWidget
from PyQt5 import QtWidgets
from dialog import ConfigDialog, CANDIDATE_COLORS
from config import sensor_config as default_sensor_config

# Create a minimal FakeParent that provides the necessary attributes and methods.
class FakeParent(QWidget):
    def __init__(self):
        super().__init__()
        # Copy the default sensor configuration to ensure all required keys exist.
        self.sensor_config = [dict(item) for item in default_sensor_config]
        # Provide dummy implementations for methods expected by ConfigDialog.
        self.reinitialize_plot_lines = lambda: None
        self.refresh_statistics_panel = lambda: None

def test_get_unique_color(qtbot):
    fake_parent = FakeParent()
    qtbot.addWidget(fake_parent)
    dialog = ConfigDialog(fake_parent)
    # Set parent's sensor_config to a known state.
    fake_parent.sensor_config = [
        {"color": "red", "name": "Red Sensor"},
        {"color": "green", "name": "Green Sensor"}
    ]
    unique_color = dialog.get_unique_color()
    # Ensure the returned color is not "red" or "green".
    assert unique_color.lower() not in {"red", "green"}
    # Also, check that it is one of the candidate colors.
    assert unique_color in CANDIDATE_COLORS

def test_save_changes_updates_config(qtbot):
    fake_parent = FakeParent()
    qtbot.addWidget(fake_parent)
    dialog = ConfigDialog(fake_parent)
    # Set up sensor_entries with predetermined QLineEdit values.
    dialog.sensor_entries = [{
        "channel": QtWidgets.QLineEdit("1"),
        "name": QtWidgets.QLineEdit("TestSensor"),
        "scale": QtWidgets.QLineEdit("600"),
        "calibration": QtWidgets.QLineEdit("1"),
        "offset": QtWidgets.QLineEdit("2"),
        "color": QtWidgets.QLineEdit("blue")
    }]
    # Call save_changes() which should update fake_parent.sensor_config.
    dialog.save_changes()
    updated_config = fake_parent.sensor_config
    # Check that the configuration was updated correctly.
    assert updated_config[0]["name"] == "TestSensor"
    assert updated_config[0]["color"] == "blue"
    # Also, ensure that scale and calibration are at least 1.
    assert updated_config[0]["scale"] >= 1
    assert updated_config[0]["calibration"] >= 1
