import pytest
from sensor import Sensor, SensorError
from config import ADC_MAX, VOLTAGE_FULL_SCALE, POLL_INTERVAL_MS

@pytest.mark.non_gui
def test_sensor_invalid_config():
    """
    Test that initializing a Sensor with a None modbus_client raises a SensorError.
    """
    dummy_config = [{"channel": 1, "scale": 600, "offset": 0, "calibration": 1}]
    with pytest.raises(SensorError) as excinfo:
        # Pass dummy_config and None for modbus_client.
        Sensor(dummy_config, None)
    assert "not initialized" in str(excinfo.value).lower()

@pytest.mark.non_gui
def test_sensor_timeout(monkeypatch):
    """
    Test sensor behavior when a reading returns an error.
    """
    dummy_config = [{"channel": 1, "scale": 600, "offset": 2, "calibration": 1}]

    class DummyErrorResponse:
        def isError(self):
            return True

    class DummyModbusClient:
        def read_holding_registers(self, address, count, slave):
            return DummyErrorResponse()

        def connect(self):
            return True

        def close(self):
            pass

    dummy_client = DummyModbusClient()
    sensor = Sensor(dummy_config, dummy_client)
    sensor_values, _ = sensor.get_reading()
    assert sensor_values[0] is None

@pytest.mark.non_gui
def test_sensor_out_of_range(monkeypatch):
    """
    Test that Sensor processes an out-of-range reading as expected.
    """
    dummy_config = [{"channel": 1, "scale": 600, "offset": 0, "calibration": 1}]

    class DummyModbusResponse:
        def __init__(self, registers):
            self.registers = registers

        def isError(self):
            return False

    class DummyModbusClient:
        def read_holding_registers(self, address, count, slave):
            # Return a value out-of-range, e.g., 5000 (which is > ADC_MAX)
            return DummyModbusResponse([5000])

        def connect(self):
            return True

        def close(self):
            pass

    dummy_client = DummyModbusClient()
    sensor = Sensor(dummy_config, dummy_client)
    sensor_values, _ = sensor.get_reading()

    expected_voltage = (5000 / ADC_MAX) * VOLTAGE_FULL_SCALE
    expected_value = (
        (expected_voltage / VOLTAGE_FULL_SCALE)
        * dummy_config[0]["scale"]
        * dummy_config[0]["calibration"]
    )
    assert sensor_values[0] == expected_value
