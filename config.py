"""
config.py

This module defines the default sensor configuration for HydroPowerSensorPlotter
and provides helper functions to save and load the sensor configuration using QSettings.
The configuration is stored as a JSON string in a persistent storage (e.g., Windows Registry
or a configuration file on other systems).
"""


import logging
import json

from PyQt5.QtCore import QSettings

# Set up a module-level logger.
logger = logging.getLogger(__name__)

# ===== Default sensor configuration ========================================================================== #
# Each dictionary represents a sensor with its parameters such as channel number, name, scale, color, style, and offset.
sensor_config = [
    {"channel": 1, "name": "Main Pressure", "scale": 600, "color": "r", "style": "-", "offset": 2},
    {"channel": 2, "name": "Charge Pressure", "scale": 600, "color": "orange", "style": "-", "offset": 2},
    {"channel": 3, "name": "Flow", "scale": 1150, "color": "b", "style": "-", "calibration": 1.1, "offset": 2},
    {"channel": 4, "name": "RPM", "scale": 1000, "color": "g", "style": "-", "offset": 2}
]
# ============================================================================================================= #

def save_sensor_config(config):
    """
    Save the sensor configuration to persistent storage using QSettings.
    
    Args:
        config (list): A list of dictionaries, each containing sensor configuration parameters.
    
    The configuration is converted to a JSON string before saving.
    """
    settings = QSettings("MyCompany", "HydroPowerSensorPlotter")
    # Convert the configuration to a JSON string and store it with the key 'sensor_config'.
    settings.setValue("sensor_config", json.dumps(config))

def load_sensor_config(default_config):
    """
    Load the sensor configuration from persistent storage.
    
    Args:
        default_config (list): The default sensor configuration to use if no configuration is stored
                               or if there is an error during loading.
    
    Returns:
        list: The stored sensor configuration if available and valid, otherwise a copy of the default configuration.
    """
    settings = QSettings("MyCompany", "HydroPowerSensorPlotter")
    config_str = settings.value("sensor_config", "")
    if config_str:
        try:
            # Attempt to load and return the configuration from the JSON string
            return json.loads(config_str)
        except Exception as e:
            logger.error("Error loading sensor config: %s", e)
            # Return a copy of the default configuration if there's an error
            return default_config.copy()
    else:
        # If nothing is stored, return a copy of the default configuration
        return default_config.copy()
