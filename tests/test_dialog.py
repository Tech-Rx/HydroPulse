import pytest
from PyQt5.QtWidgets import QWidget
from dialog import ConfigDialog, CANDIDATE_COLORS

# Create a simple FakeParent class that extends QWidget and has a sensor_config attribute.
class FakeParent(QWidget):
    def __init__(self):
        super().__init__()
        # Initialize sensor_config with some test data.
        self.sensor_config = [
            {"color": "red"},
            {"color": "green"}
        ]

def test_get_unique_color(qtbot):
    # Create an instance of FakeParent.
    fake_parent = FakeParent()
    qtbot.addWidget(fake_parent)
    
    # Instantiate ConfigDialog with fake_parent.
    dialog = ConfigDialog(fake_parent)
    # Call get_unique_color and ensure the returned color is not red or green.
    unique_color = dialog.get_unique_color()
    assert unique_color.lower() not in {"red", "green"}
    # Also, ensure it is one of the candidate colors.
    assert unique_color in CANDIDATE_COLORS
