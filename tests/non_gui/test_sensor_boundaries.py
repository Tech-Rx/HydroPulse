# test_sensor_boundaries.py
import pytest
from sensor import Sensor, SensorError
from config import ADC_MAX, VOLTAGE_FULL_SCALE


# Fake modbus response and clients for boundary conditions.
class FakeModbusResponse:
    def __init__(self, registers):
        self.registers = registers

    def isError(self):
        return False


class FakeModbusClient:
    def __init__(self, registers):
        self.registers = registers

    def read_holding_registers(self, address, count, slave):
        return FakeModbusResponse(self.registers)

    def connect(self):
        return True

    def close(self):
        pass


@pytest.fixture
def sensor_config_example():
    # Simple configuration for one sensor.
    return [
        {
            "channel": 1,
            "scale": 600,
            "offset": 2,
            "calibration": 1,
            "name": "Boundary Sensor",
            "color": "blue",
            "style": "-",
        }
    ]

@pytest.mark.non_gui
def test_sensor_reading_at_zero(sensor_config_example):
    """
    Test sensor reading when raw value is 0.
    Expect: raw value = max(0, 0 - offset) -> 0, voltage = 0.
    Processed value should be 0.
    """
    client = FakeModbusClient([0])
    sensor = Sensor(sensor_config_example, client)
    sensor_values, _ = sensor.get_reading()
    assert sensor_values[0] == 0, "Expected processed value 0 when raw value is 0."

@pytest.mark.non_gui
def test_sensor_reading_at_max(sensor_config_example):
    """
    Test sensor reading when raw value equals ADC_MAX.
    Expect: raw = ADC_MAX - offset, voltage accordingly, then processed.
    """
    client = FakeModbusClient([ADC_MAX])
    sensor = Sensor(sensor_config_example, client)
    sensor_values, _ = sensor.get_reading()
    # Calculation:
    # raw = ADC_MAX - 2, voltage = ((ADC_MAX - 2) / ADC_MAX) * VOLTAGE_FULL_SCALE,
    # processed = (voltage / VOLTAGE_FULL_SCALE) * 600.
    expected = ((ADC_MAX - 2) / ADC_MAX) * 600
    assert (
        abs(sensor_values[0] - expected) < 1
    ), "Sensor reading at ADC_MAX not as expected."

@pytest.mark.non_gui
def test_sensor_invalid_reading_type(sensor_config_example):
    """
    Test that a non-numeric sensor reading raises a SensorError.
    """

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

    client = DummyModbusClient()
    sensor = Sensor(sensor_config_example, client)
    with pytest.raises(SensorError):
        sensor.get_reading()
