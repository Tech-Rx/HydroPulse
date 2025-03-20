# test_config.py
import pytest
import json
from PyQt5.QtCore import QSettings
from config import load_sensor_config, sensor_config, save_sensor_config

@pytest.fixture(autouse=True)
def clear_settings():
    """
    Fixture that clears QSettings for the HydroPowerSensorPlotter application before each test.
    """
    settings = QSettings("MyCompany", "HydroPowerSensorPlotter")
    settings.clear()

def test_load_default_config_when_empty():
    """
    Test that load_sensor_config returns a copy of the default configuration 
    when no configuration is stored.
    """
    loaded_config = load_sensor_config(sensor_config)
    # Assert that the loaded configuration is equal to the default configuration.
    assert loaded_config == sensor_config

def test_save_and_load_config():
    """
    Test that saving a modified configuration and then loading it returns the modified configuration.
    """
    # Create a modified configuration.
    test_config = sensor_config.copy()
    test_config[0]["name"] = "Test Sensor"
    
    # Save the modified configuration.
    save_sensor_config(test_config)
    
    # Load the configuration.
    loaded_config = load_sensor_config(sensor_config)
    # Check that the first sensor's name matches the modified value.
    assert loaded_config[0]["name"] == "Test Sensor"
