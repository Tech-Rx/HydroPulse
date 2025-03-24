# tests/test_config.py
import pytest
import os
import json
import copy  # Add this import
from config import load_sensor_config, sensor_config, save_sensor_config, CONFIG_FILE

@pytest.fixture(autouse=True)
def clear_config_file():
    """Fixture to remove config file before/after each test"""
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
    yield
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)

@pytest.mark.non_gui  # Add this marker
def test_load_default_config_when_empty():
    loaded = load_sensor_config(sensor_config)
    assert loaded == sensor_config

@pytest.mark.non_gui  # Add this marker
def test_save_and_load_config():
    # Create a DEEP copy to avoid modifying original config
    test_config = copy.deepcopy(sensor_config)
    test_config[0]["name"] = "Test Sensor"
    
    save_sensor_config(test_config)
    loaded = load_sensor_config(sensor_config)  # Pass original as default
    
    assert loaded[0]["name"] == "Test Sensor", "Modified name not preserved"
    assert loaded[1:] == sensor_config[1:], "Other entries should remain unchanged"