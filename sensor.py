"""
sensor.py - Sensor abstraction for HydroPulse

This module provides a Sensor class for reading sensor data from a Modbus client.
It processes raw sensor values by applying an offset, scaling, and calibration,
and returns the processed data along with a timestamp.
It also defines a SensorError exception for handling sensor-related errors.

Optional:
    - Thread-safety: By passing use_mutex=True, a QMutex is used to protect get_reading().
    - This design remains synchronous; if needed, you can later offload get_reading() to a worker thread.
"""


from datetime import datetime
import logging
from pymodbus.client import ModbusSerialClient as ModbusClient
from PyQt5 import QtCore  # for QMutex if needed

# Set up a module-level logger.
logger = logging.getLogger(__name__)

# =========================
# Configuration Constants
# =========================
ADC_MAX = 4095
VOLTAGE_FULL_SCALE = 10
POLL_INTERVAL_MS = 250 # Optional: used for polling intervals

class SensorError(Exception):
    """Custom exception raised when sensor-related errors occur."""
    pass
    
class Sensor:
    def __init__(self, sensor_config, modbus_client, use_mutex=False):
        """
        Initialize the Sensor abstraction.
        
        Args:
            sensor_config (list): List of sensor configuration dictionaries.
                Each dictionary should contain at least:
                    - "channel": (int) The sensor channel (1-indexed)
                    - "scale": (float) The scaling factor (mandatory)
                    - "offset": (float, optional) Offset value (default: 0)
                    - "calibration": (float, optional) Calibration factor (default: 1)
            modbus_client (ModbusClient): The modbus client for communication.
            use_mutex (bool): Optional; if True, a QMutex will be used for thread safety.
        
        Raises:
            SensorError: If modbus_client is not provided.
        """
        if not modbus_client:
            raise SensorError("Modbus client is not initialized.")
        self.sensor_config = sensor_config
        self.modbus_client = modbus_client

        # Optional thread-safety.
        self.use_mutex = use_mutex
        self.mutex = QtCore.QMutex() if use_mutex else None

    def get_reading(self):
        """
        Read sensor data from the Modbus client, process the raw values,
        and return the processed sensor values along with a timestamp.

        Returns:
            tuple: (sensor_values, timestamp)
                sensor_values (list): A list of processed sensor values.
                timestamp (float): Current timestamp as returned by datetime.now().timestamp()

        Raises:
            SensorError: If reading from the modbus client fails.
        """
        if self.use_mutex and self.mutex:
            self.mutex.lock()
        try:
            sensor_values = []
            # Iterate over each sensor configuration
            for sensor in self.sensor_config:
                channel = sensor.get("channel", 1)
                # Read the corresponding register (channels are 1-indexed)
                response = self.modbus_client.read_holding_registers(
                    address=channel - 1, count=1, slave=1
                )
                if response.isError():
                    # Log the error and append None to indicate a failed reading
                    logger.error(f"Error reading sensor on channel {channel}: {response}")
                    sensor_values.append(None)

                else:
                    raw_val = response.registers[0]
                    # Ensure raw_val is a number
                    try:
                        raw_val_numeric = float(raw_val)
                    except Exception:
                        raise SensorError(f"Invalid sensor reading: {raw_val}")

                    # Process the raw value: apply offset, convert to voltage,
                    # and then apply scaling and calibration.
                    processed_val = max(0, raw_val_numeric - sensor.get("offset", 0))
                    voltage = (processed_val / ADC_MAX) * VOLTAGE_FULL_SCALE
                    calibration = sensor.get("calibration", 1)
                    # Assume 'scale' is a mandatory key in sensor configuration.
                    sensor_value = (voltage / VOLTAGE_FULL_SCALE) * sensor["scale"] * calibration
                    sensor_values.append(sensor_value)
            current_time = datetime.now().timestamp()
            return sensor_values, current_time
        finally:
            if self.use_mutex and self.mutex:
                self.mutex.unlock()
            
    def disconnect(self):
        """
        Disconnect the sensor by closing the modbus client connection.
        """
        self.modbus_client.close()
        logger.info("Modbus client disconnected.")
