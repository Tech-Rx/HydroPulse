# test_configuration_persistence.py
import pytest
from config import save_sensor_config, load_sensor_config, sensor_config
from PyQt5.QtCore import QSettings


class DummySettings:
    """A dummy settings class to simulate QSettings behavior in memory."""

    def __init__(self):
        self.data = {}

    def setValue(self, key, value):
        self.data[key] = value

    def value(self, key, defaultValue=None):
        return self.data.get(key, defaultValue)

    def remove(self, key):
        if key in self.data:
            del self.data[key]


@pytest.fixture(autouse=True)
def dummy_qsettings(monkeypatch):
    dummy = DummySettings()
    monkeypatch.setattr(QSettings, "__init__", lambda self, org, app: None)
    monkeypatch.setattr(QSettings, "setValue", dummy.setValue)
    monkeypatch.setattr(QSettings, "value", dummy.value)
    monkeypatch.setattr(QSettings, "remove", dummy.remove)
    return dummy

@pytest.mark.non_gui  # Add this marker
def test_configuration_persistence(dummy_qsettings):
    """
    Test that saving sensor configuration and then loading it returns the same configuration.
    """
    # Use a modified sensor configuration.
    new_config = [
        {
            "channel": 2,
            "scale": 500,
            "offset": 5,
            "calibration": 1.2,
            "name": "Persistent Sensor",
            "color": "green",
            "style": "-",
        }
    ]
    # Save configuration.
    save_sensor_config(new_config)
    # Load configuration.
    loaded_config = load_sensor_config(sensor_config)
    assert (
        loaded_config == new_config
    ), "Loaded configuration does not match saved configuration."
