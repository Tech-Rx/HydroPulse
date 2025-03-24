"""
sensor_worker.py - Sensor worker thread for HydroPulse

This module provides the SensorWorker class, a QThread subclass responsible for
continuously polling a Sensor instance. It emits processed sensor data and
timestamps via signals and handles any errors encountered during sensor
readings. The module ensures thread safety and orderly shutdown of the
sensor polling process.
"""

from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker, QObject
from sensor import Sensor
import logging
from typing import Optional
from config import POLL_INTERVAL_MS

logger = logging.getLogger(__name__)


class SensorWorker(QThread):
    """
    SensorWorker is a QThread subclass that continuously polls a sensor for
    data. It emits signals with sensor readings and handles any errors that
    occur during the sensor reading process.

    Attributes:
        data_ready (pyqtSignal): Emitted with sensor values and a timestamp.
        error_occurred (pyqtSignal): Emitted when an error occurs during
        sensor reading.
    """
    # Signal to emit sensor data and timestamp
    data_ready = pyqtSignal(list, float)
    error_occurred = pyqtSignal(str)  # Fixed signal declaration

    def __init__(
        self,
        sensor: Sensor,
        poll_interval: int = POLL_INTERVAL_MS,
        parent: Optional[QObject] = None,  # Use QObject directly
    ) -> None:
        """
        Initialize the SensorWorker thread.

        Args:
            sensor (Sensor): The sensor instance to poll.
            poll_interval (int): The interval in ms between sensor polls.
            parent (Optional[QObject]): An optional parent QObject.
        """
        super().__init__(parent)
        self.sensor = sensor
        self.poll_interval = poll_interval
        # Mutex to synchronize access to _running flag.
        self._mutex = QMutex()
        self._running = False

    def run(self) -> None:
        """
        Main execution loop for the SensorWorker thread.

        This method continuously polls the sensor for readings as long as the
        thread is running. It emits sensor data via the data_ready signal and
        errors via the error_occurred signal. The polling interval is
        maintained by sleeping for the specified number of ms between reads.
        """
        """Main execution loop for the thread"""
        with QMutexLocker(self._mutex):
            self._running = True

        logger.info("SensorWorker thread started")

        try:
            while self.is_running():
                try:
                    # Retrieve sensor readings and associated timestamp.
                    sensor_values, timestamp = self.sensor.get_reading()
                    # Emit the sensor values and timestamp to connected slots.
                    self.data_ready.emit(sensor_values, timestamp)
                except Exception as e:
                    logger.error("Error in SensorWorker: %s", e)
                    self.error_occurred.emit(str(e))
                finally:
                    # Pause execution for the defined polling interval.
                    self.msleep(self.poll_interval)
        finally:
            with QMutexLocker(self._mutex):
                self._running = False
            logger.info("SensorWorker thread stopped")

    def is_running(self):
        """
        Check whether the SensorWorker thread is currently running in a
        thread-safe manner.

        Returns:
            bool: True if the thread is set to run; False otherwise.
        """
        """Thread-safe running check"""
        with QMutexLocker(self._mutex):
            return self._running

    def stop(self):
        """
        Stop the SensorWorker thread in an orderly fashion.

        This method sets the running flag to False, signals the thread to quit,
        and waits for up to 2 seconds for a graceful shutdown. If the thread
        does not terminate in time, it forces termination.
        """
        """Orderly thread shutdown"""
        logger.debug("Stopping SensorWorker...")

        with QMutexLocker(self._mutex):
            self._running = False

        # Signal the thread to stop and attempt graceful shutdown.
        self.quit()
        if not self.wait(2000):  # 2 second timeout
            logger.warning("Forcing thread termination")
            self.terminate()

        logger.info("SensorWorker stopped confirmed")
