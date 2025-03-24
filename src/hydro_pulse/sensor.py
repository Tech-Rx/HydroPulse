"""
sensor.py - Sensor abstraction for HydroPulse

This module provides a Sensor class for reading sensor. It processes raw
sensor values by applying an offset, scaling, and calibration,and returns the
processed data along with a timestamp. It also defines a SensorError exception
for handling sensor-related errors.
"""

from datetime import datetime
import logging
import time
import threading
from typing import Any, List, Dict, Tuple, Optional

from contextlib import nullcontext

from pymodbus.client import ModbusSerialClient as ModbusClient

from config import ADC_MAX, VOLTAGE_FULL_SCALE

# Set up a module-level logger.
logger = logging.getLogger(__name__)


class SensorError(Exception):
    """Custom exception raised when sensor-related errors occur."""

    pass


class Sensor:
    def __init__(
        self,
        sensor_config: List[Dict[str, Any]],
        modbus_client: ModbusClient,
        use_mutex: bool = False,
    ) -> None:
        """
        Initialize the Sensor abstraction.

        Args:
            sensor_config (list): List of sensor configuration dictionaries.
                Each dictionary should contain at least:
                    - "channel": (int) The sensor channel (1-indexed)
                    - "scale": (float) The scaling factor (mandatory)
                    - "offset": (float, optional) Offset value (default: 2)
                    - "calibration": (float) Calibration factor (def: 1)
            modbus_client (ModbusClient): The modbus client for communication.
            use_mutex (bool): Opt; use threading.Lock for thread safety.

        Raises:
            SensorError: If modbus_client is not provided.
        """
        if not modbus_client:
            raise SensorError("Modbus client is not initialized.")
        self.sensor_config = sensor_config
        self.modbus_client = modbus_client
        self.use_mutex = use_mutex
        self.mutex = threading.Lock() if use_mutex else None

    def get_reading(self) -> Tuple[List[Optional[float]], float]:
        """
        Read sensor data from the Modbus client, process the raw values,
        and return the processed sensor values along with a timestamp.

        Returns:
            tuple: (sensor_values, timestamp)
                sensor_values (list): A list of processed sensor values.
                timestamp (float): Current timestamp.

        Raises:
            SensorError: If reading from the modbus client fails.
        """
        # Use a context manager for mutex handling.
        # otherwise, use a no-op context.
        context = (
            self.mutex
            if self.use_mutex and self.mutex
            else nullcontext()
        )
        with context:
            sensor_values: List[Optional[float]] = []
            # Iterate over each sensor configuration
            for sensor in self.sensor_config:
                channel = sensor.get("channel", 1)
                retries = 3  # Try 3 times
                attempt = 0
                response = None
                reading_obtained = False

                while attempt < retries and not reading_obtained:
                    try:
                        # Modbus device uses 0-based addressing
                        response = self.modbus_client.read_holding_registers(
                            address=channel - 1, count=1, slave=1
                        )
                        # If response is an error, raise a trigger to retry.
                        if response is None or response.isError():
                            logger.error(
                                "Failed to read channel %s on attempt %s",
                                channel,
                                attempt + 1,
                            )
                            attempt += 1
                            if attempt >= retries:
                                break
                            time.sleep(2**attempt)
                        else:
                            reading_obtained = True
                            # Success: break out of the retry loop.
                            break
                    except Exception as e:
                        logger.error(
                            (
                                "Attempt %s: Exception reading sensor on "
                                "channel %s: %s"
                            ),
                            attempt + 1,
                            channel,
                            e,
                        )
                        attempt += 1
                        if attempt == retries:
                            break
                        time.sleep(2**attempt)  # Exponential backoff

                # Process the response if a valid one was obtained.
                if reading_obtained:
                    try:
                        raw_val = response.registers[0]
                        # Ensure raw_val is a number
                        raw_val_numeric = float(raw_val)
                        # Process the raw value, apply offset,
                        # convert to voltage, and then apply
                        # scaling and calibration.
                        processed_val = max(
                            0, raw_val_numeric - sensor.get("offset", 0)
                        )
                        voltage = (
                            (processed_val / ADC_MAX)
                            * VOLTAGE_FULL_SCALE
                        )
                        calibration = sensor.get("calibration", 1)
                        # scale is a mandatory key in sensor configuration.
                        sensor_value = (
                            (voltage / VOLTAGE_FULL_SCALE)
                            * sensor["scale"]
                            * calibration
                        )
                        sensor_values.append(sensor_value)  # <-- Append here
                    except Exception:
                        error_msg = (
                            f"Invalid reading on channel {channel}"
                        )
                        raise SensorError(error_msg)
                else:
                    # Ensure an entry for each sensor
                    sensor_values.append(None)
            current_time = datetime.now().timestamp()
            return sensor_values, current_time

    def disconnect(self):
        """
        Disconnect the sensor by closing the modbus client connection.
        """
        self.modbus_client.close()
        logger.info("Modbus client disconnected.")
