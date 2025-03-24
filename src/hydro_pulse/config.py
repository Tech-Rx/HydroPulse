"""
config.py

This module defines the default sensor configuration for HydroPulse and provides
helper functions to save and load the sensor configuration using QSettings.
On Windows, QSettings stores configuration data in the registry.
"""

import json
import copy
import logging
import threading
from typing import Any, List, Dict
from PyQt5.QtCore import QSettings

# Set up a module-level logger.
logger = logging.getLogger(__name__)

# Global lock to avoid race conditions
CONFIG_LOCK = threading.Lock()

# QSettings organization and application names
ORGANIZATION_NAME = 'HydroPulse'
APPLICATION_NAME = 'HydroPulseApp'
SETTINGS_KEY_SENSOR_CONFIG = "sensor_config"

# ===== Default sensor configuration ======================================= #
# Each dictionary represents a sensor with its parameters such as channel no,
# name, scale, color, style, calibration, and offset.
sensor_config: List[Dict[str, Any]] = [
    {
        "channel": 1,
        "name": "Main Pressure",
        "scale": 600,
        "color": "r",
        "style": "-",
        "calibration": 1,
        "offset": 2,
    },
    {
        "channel": 2,
        "name": "Charge Pressure",
        "scale": 600,
        "color": "orange",
        "style": "-",
        "calibration": 1,
        "offset": 2,
    },
    {
        "channel": 3,
        "name": "Flow",
        "scale": 600,
        "color": "b",
        "style": "-",
        "calibration": 1,
        "offset": 2,
    },
    {
        "channel": 4,
        "name": "RPM",
        "scale": 600,
        "color": "g",
        "style": "-",
        "calibration": 1,
        "offset": 2,
    },
]

# ========================================================================== #
# Sensor Polling Constants
# ========================================================================== #
ADC_MAX = 4095
VOLTAGE_FULL_SCALE = 10
POLL_INTERVAL_MS = 100  # Polling interval in milliseconds

# ========================================================================== #
# Plotting and UI Constants
# ========================================================================== #
Y_AXIS_MAX = 1150
TIME_WINDOW_SEC = 300  # 5 minutes

# Define a maximum number of points to store corresponding to a 5-minute window.
MAX_POINTS = int(TIME_WINDOW_SEC * 1000 / POLL_INTERVAL_MS)


def validate_config(config: List[Dict[str, Any]]) -> bool:
    """
    Validate the sensor configuration.
    Ensures that every sensor dictionary contains the required keys.

    Args:
        config: List of sensor configuration dictionaries.

    Returns:
        True if all dicts have the keys; False otherwise.
    """
    required_keys = {"channel", "name", "scale", "color"}
    return all(required_keys.issubset(sensor.keys()) for sensor in config)


def load_sensor_config(default_config: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Load the sensor configuration from the system registry using QSettings.

    Args:
        default_config: The default sensor configuration to use if no
                        configuration is stored or if there is an error during loading.

    Returns:
        The stored sensor configuration if available and valid, otherwise a copy of the default configuration.
    """
    with CONFIG_LOCK:
        settings = QSettings(ORGANIZATION_NAME, APPLICATION_NAME)
        config_str = settings.value(SETTINGS_KEY_SENSOR_CONFIG, "")
        if config_str:
            try:
                loaded_config = json.loads(config_str)
                if validate_config(loaded_config):
                    return loaded_config
                logger.error("Invalid config format, using defaults")
            except Exception as e:
                logger.error("Error parsing config: %s", e)
        else:
            logger.info("No stored config found, using defaults")
        # Return a fresh copy of the defaults if loading fails
        return copy.deepcopy(default_config)


def save_sensor_config(config: List[Dict[str, Any]]) -> None:
    """
    Save the sensor configuration to the system registry using QSettings.

    Args:
        config: A list of dictionaries containing sensor configurations.
    """
    with CONFIG_LOCK:
        settings = QSettings(ORGANIZATION_NAME, APPLICATION_NAME)
        try:
            config_str = json.dumps(config)
            settings.setValue(SETTINGS_KEY_SENSOR_CONFIG, config_str)
        except Exception as e:
            logger.error("Error saving config: %s", e)
            raise


if __name__ == "__main__":
    # Simple test to verify saving and loading works.
    try:
        save_sensor_config(sensor_config)
        loaded = load_sensor_config(sensor_config)
        assert sensor_config == loaded, "Config mismatch"
        print("Configuration test passed")
    except Exception as e:
        print(f"Configuration test failed: {e}")
