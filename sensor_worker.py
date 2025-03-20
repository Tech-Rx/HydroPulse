from PyQt5 import QtCore
from sensor import Sensor, SensorError, POLL_INTERVAL_MS
import logging

logger = logging.getLogger(__name__)

class SensorWorker(QtCore.QThread):
    # Signal to emit sensor data and timestamp.
    data_ready = QtCore.pyqtSignal(list, float)

    def __init__(self, sensor, poll_interval=POLL_INTERVAL_MS, parent=None):
        """
        Initialize the sensor worker.
        
        Args:
            sensor (Sensor): An instance of your Sensor class.
            poll_interval (int): Polling interval in milliseconds.
            parent (QObject, optional): Parent object.
        """
        super().__init__(parent)
        self.sensor = sensor
        self.poll_interval = poll_interval
        self._running = True

    def run(self):
        """Main loop: continuously poll the sensor and emit data."""
        while self._running:
            try:
                sensor_values, timestamp = self.sensor.get_reading()
                self.data_ready.emit(sensor_values, timestamp)
            except Exception as e:
                # Catch all exceptions (including ModbusIOException) to prevent thread crash.
                logger.error("Error in SensorWorker: %s", e)
                # Optionally, you can also emit a signal indicating an error.
            self.msleep(self.poll_interval)

    def stop(self):
        """Stop the worker thread."""
        self._running = False
        self.wait()
