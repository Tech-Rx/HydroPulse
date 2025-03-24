# tests/gui/test_sensor_worker.py
import pytest
import time
import logging
from PyQt5.QtCore import QObject
from sensor_worker import SensorWorker
from sensor import Sensor
from unittest.mock import Mock

logger = logging.getLogger(__name__)

# --------------------------
# Fixtures
# --------------------------
@pytest.fixture
def mock_sensor():
    """Mock sensor that returns predictable values"""
    sensor = Mock(spec=Sensor)
    sensor.get_reading.return_value = ([100.0], time.time())
    return sensor

@pytest.fixture
def worker(mock_sensor):
    """Worker instance with mock sensor"""
    return SensorWorker(mock_sensor, 100)

# --------------------------
# Test Cases
# --------------------------
def test_worker_start_stop(worker, qtbot):
    """Test basic start/stop functionality"""
    worker.start()
    
    # Verify thread starts
    qtbot.waitUntil(worker.is_running, timeout=2000)
    assert worker.isRunning()
    
    # Stop and verify
    worker.stop()
    qtbot.waitUntil(lambda: not worker.is_running(), timeout=3000)
    assert not worker.isRunning()

def test_data_emission(worker, qtbot, mock_sensor):
    """Verify data is emitted when worker runs"""
    with qtbot.waitSignal(worker.data_ready, timeout=1500):
        worker.start()
        qtbot.waitUntil(worker.is_running)

def test_error_handling(worker, qtbot, mock_sensor):
    """Test error signal emission"""
    mock_sensor.get_reading.side_effect = Exception("Simulated error")
    
    with qtbot.waitSignal(worker.error_occurred, timeout=1000):
        worker.start()
        qtbot.waitUntil(worker.is_running)

def test_forced_termination(worker, qtbot, mock_sensor):
    """Test fallback to terminate() when quit fails"""
    worker.start()
    qtbot.waitUntil(worker.is_running)
    
    # Prevent normal shutdown
    mock_sensor.get_reading.side_effect = lambda: time.sleep(5)
    
    worker.stop()
    qtbot.wait(2500)  # Wait past 2s timeout
        
    assert not worker.isRunning()

def test_thread_safety(worker, qtbot):
    """Verify mutex-protected running flag"""
    worker.start()
    qtbot.waitUntil(worker.is_running, timeout=2000)
    
    # Check actual thread state
    assert worker.isRunning()  # QThread's status
    
    # Stop properly via mutex-protected method
    worker.stop()
    qtbot.waitUntil(lambda: not worker.is_running(), timeout=3000)
    
    # Verify both internal flag and thread state
    assert not worker.is_running()
    assert not worker.isRunning()
