# tests/test_sensor_error.py
import pytest
from sensor import Sensor, SensorError
import time

class FakeErrorResponse:
    def __init__(self):
        self.registers = []

    def isError(self):
        return True

class FakeErrorModbusClient:
    def read_holding_registers(self, address, count, slave):
        return FakeErrorResponse()

    def connect(self):
        return True

    def close(self):
        pass

@pytest.fixture
def fake_error_modbus_client():
    return FakeErrorModbusClient()

@pytest.fixture
def sensor_config_error():
    return [{
        "channel": 1,
        "scale": 600,
        "offset": 2,
        "calibration": 1,
        "name": "Error Sensor",
        "color": "r",
        "style": "-",
    }]
@pytest.mark.non_gui
def test_sensor_error_get_reading(sensor_config_error, fake_error_modbus_client):
    """Test sensor error handling without Qt dependencies"""
    sensor = Sensor(sensor_config_error, fake_error_modbus_client)
    sensor_values, _ = sensor.get_reading()
    assert sensor_values[0] is None, "Failed reading should return None"