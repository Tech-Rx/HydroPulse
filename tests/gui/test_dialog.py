import pytest
from PyQt5.QtWidgets import QWidget, QDialog
from dialog import ConfigDialog, CANDIDATE_COLORS


# Create a simple FakeParent class that extends QWidget and has a sensor_config attribute.
class FakeParent(QWidget):
    def __init__(self):
        super().__init__()
        # Initialize sensor_config with some test data.
        self.sensor_config = [{"color": "red"}, {"color": "green"}]

@pytest.mark.gui  # Add this marker
def test_get_unique_color(qtbot, monkeypatch):
    # Override exec_ so it doesn't block.
    def fake_exec(self):
        print("exec_ was called but overridden!")
        return QDialog.Accepted  # Simulate an accepted dialog

    monkeypatch.setattr(ConfigDialog, "exec_", fake_exec)

    print("Creating FakeParent")
    # Create an instance of FakeParent.
    fake_parent = FakeParent()
    qtbot.addWidget(fake_parent)

    print("Instantiating ConfigDialog")
    # Instantiate ConfigDialog with fake_parent.
    dialog = ConfigDialog(fake_parent)
    qtbot.wait(100)  # allow events to process

    print("Calling get_unique_color")
    # Call get_unique_color and ensure the returned color is not red or green.
    unique_color = dialog.get_unique_color()
    assert unique_color.lower() not in {"red", "green"}
    # Also, ensure it is one of the candidate colors.
    assert unique_color in CANDIDATE_COLORS
