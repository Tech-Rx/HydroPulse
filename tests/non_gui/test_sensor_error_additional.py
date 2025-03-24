import pytest
from sensor import Sensor, SensorError

@pytest.mark.non_gui
def test_sensor_connection_failure(monkeypatch):
    """
    Test that a sensor connection failure is handled by returning None for that sensor.
    """
    dummy_config = [{"channel": 1, "scale": 600, "offset": 2, "calibration": 1}]

    class DummyResponse:
        def isError(self):
            return True

    class DummyModbusClient:
        def read_holding_registers(self, address, count, slave):
            return DummyResponse()

        def connect(self):
            return True

        def close(self):
            pass

    dummy_client = DummyModbusClient()
    sensor = Sensor(dummy_config, dummy_client)
    sensor_values, _ = sensor.get_reading()
    assert sensor_values[0] is None

@pytest.mark.non_gui
def test_sensor_invalid_reading(monkeypatch):
    """
    Test that if a sensor reading is invalid (non-numeric), the Sensor raises SensorError.
    """
    dummy_config = [{"channel": 1, "scale": 600, "offset": 2, "calibration": 1}]

    class DummyInvalidResponse:
        def __init__(self):
            self.registers = ["invalid"]

        def isError(self):
            return False

    class DummyModbusClient:
        def read_holding_registers(self, address, count, slave):
            return DummyInvalidResponse()

        def connect(self):
            return True

        def close(self):
            pass

    dummy_client = DummyModbusClient()
    sensor = Sensor(dummy_config, dummy_client)
    with pytest.raises((ValueError, SensorError)):
        sensor.get_reading()
