# tests/test_config_dialog.py
from ui import SensorPlotter
from dialog import ConfigDialog
from PyQt5 import QtCore, QtWidgets
import pytest

@pytest.mark.gui  # Add this marker
def test_open_config_dialog(qtbot, qt_app):
    """Verify config dialog opens on button click (GUI test)"""
    window = SensorPlotter()
    qtbot.addWidget(window)
    
    # Track dialog creation
    dialog_created = False
    
    def dialog_check():
        nonlocal dialog_created
        for w in QtWidgets.QApplication.topLevelWidgets():
            if isinstance(w, ConfigDialog):
                dialog_created = True
                return True
        return False
    
    # Click the config button
    qtbot.mouseClick(window.config_button, QtCore.Qt.LeftButton)
    
    # Wait for dialog with explicit widget check
    qtbot.waitUntil(dialog_check, timeout=3000)
    assert dialog_created, "ConfigDialog was not created"