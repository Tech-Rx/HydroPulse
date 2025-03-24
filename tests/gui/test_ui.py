import pytest
from PyQt5 import QtWidgets, QtCore
from ui import SensorPlotter

@pytest.mark.gui
def test_initial_status(qtbot):
    """Test that the SensorPlotter initializes with a 'Ready' status."""
    window = SensorPlotter()
    qtbot.addWidget(window)
    assert "Ready" in window.status_label.text()

@pytest.mark.gui
def test_start_stop_buttons(qtbot):
    """Test that the start button is enabled and the stop button is disabled on initialization."""
    window = SensorPlotter()
    qtbot.addWidget(window)
    assert window.start_button.isEnabled()
    assert not window.stop_button.isEnabled()

@pytest.mark.gui
def test_open_config_dialog(qtbot):
    """Test that calling open_config_dialog() opens a QDialog."""
    window = SensorPlotter()
    qtbot.addWidget(window)

    # Monkey-patch QDialog.exec_ to not block.
    original_exec = QtWidgets.QDialog.exec_
    QtWidgets.QDialog.exec_ = lambda self: None

    window.open_config_dialog()
    dialogs = [
        w
        for w in QtWidgets.QApplication.topLevelWidgets()
        if isinstance(w, QtWidgets.QDialog)
    ]
    assert len(dialogs) >= 1, "Expected at least one dialog to be open."

    # Clean up and restore
    for d in dialogs:
        d.close()
    QtWidgets.QDialog.exec_ = original_exec
