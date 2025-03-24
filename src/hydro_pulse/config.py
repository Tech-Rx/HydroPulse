"""
config.py

This module defines the default sensor configuration for HydroPulse, provides
helper functions to save and load the sensor configuration using QSettings.
The configuration is stored as a JSON string in a persistent storage.
"""

import json
import copy
import logging
import threading
from typing import Any, List, Dict

CONFIG_FILE = "sensor_config.json"

# Set up a module-level logger.
logger = logging.getLogger(__name__)

# Add a global mutex
CONFIG_LOCK = threading.Lock()

# Settings key constant
SETTINGS_KEY_SENSOR_CONFIG = "sensor_config"

# ===== Default sensor configuration ======================================= #
# Each dictionary represents a sensor with its parameters such as channel no,
# name, scale, color, style, calibration and offset.
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
POLL_INTERVAL_MS = 100  # Optional: used for polling intervals

# ========================================================================== #
# Plotting and UI Constants
# ========================================================================== #
Y_AXIS_MAX = 1150
TIME_WINDOW_SEC = 300  # 5 minutes

# Define a maximum number of points to store e.g corresponding to ur 5-min win
MAX_POINTS = int(
    TIME_WINDOW_SEC * 1000 / POLL_INTERVAL_MS
)  # Adjust based on your poll interval and desired window length


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


def load_sensor_config(
    default_config: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Load the sensor configuration from persistent storage.

    Args:
        default_config (list): The default sensor configuration to use if no
                               configuration is storedor if there is an error
                               during loading.

    Returns:
        list: The stored sensor configuration if available and valid,
              otherwise a copy of the default configuration.
    """
    with CONFIG_LOCK:
        try:
            with open(CONFIG_FILE, "r") as f:
                loaded_config = json.load(f)
                if validate_config(loaded_config):
                    return loaded_config
                logger.error("Invalid config format, using defaults")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.info("No config found, using defaults: %s", e)
        except Exception as e:
            logger.error("Error loading config: %s", e)

        # Return fresh copy of defaults if loading fails
        return copy.deepcopy(default_config)


def save_sensor_config(config: List[Dict[str, Any]]) -> None:
    """
    Save the sensor configuration to a JSON file.

    Args:
        config (list): A list of dictionaries containing sensor configurations
    """
    with CONFIG_LOCK:
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error("Error saving config: %s", e)
            raise


if __name__ == "__main__":
    # Simple test to verify saving and loading works
    try:
        save_sensor_config(sensor_config)
        loaded = load_sensor_config(sensor_config)
        assert sensor_config == loaded, "Config mismatch"
        print("Configuration test passed")
    except Exception as e:
        print(f"Configuration test failed: {e}")
