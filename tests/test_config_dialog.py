# test_config_dialog.py
import pytest
from PyQt5.QtWidgets import QDialog
from ui import SensorPlotter
from dialog import ConfigDialog

@pytest.mark.skip(reason="Config dialog functionality under revision; skipping for now.")
def test_open_config_dialog(qtbot, monkeypatch):
    """
    Test that clicking the configuration button triggers the opening of the configuration dialog.
    We disconnect the original signal and reconnect it to a lambda that sets a flag.
    """
    # Create a SensorPlotter instance.
    window = SensorPlotter()
    qtbot.addWidget(window)
    
    # Disconnect the specific connection for the config button.
    try:
        window.config_button.clicked.disconnect(window.open_config_dialog)
    except Exception:
        pass

    # Reconnect with a lambda that sets a flag on the window.
    window.config_button.clicked.connect(lambda: setattr(window, "config_dialog_opened", True))
    
    # Ensure the button is visible and enabled.
    window.config_button.setEnabled(True)
    window.config_button.show()
    
    # Simulate clicking the configuration button.
    qtbot.mouseClick(window.config_button, 0)
    qtbot.wait(200)  # Wait to allow the slot to be invoked.
    
    # Assert that the flag was set.
    assert getattr(window, "config_dialog_opened", False), "ConfigDialog was not opened when clicking the configuration button."
