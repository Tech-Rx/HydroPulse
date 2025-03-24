import pytest
from sensor import Sensor
from config import ADC_MAX, VOLTAGE_FULL_SCALE, POLL_INTERVAL_MS
from datetime import datetime


# --- Fake Modbus Response and Client for Testing ---
class FakeModbusResponse:
    def __init__(self, registers):
        self.registers = registers

    def isError(self):
        return False


class FakeModbusClient:
    def read_holding_registers(self, address, count, slave):
        # Always return a fixed register value, e.g., 2048.
        return FakeModbusResponse([2048])

    def connect(self):
        return True

    def close(self):
        pass


@pytest.fixture
def fake_modbus_client():
    return FakeModbusClient()


@pytest.fixture
def sensor_config_test():
    # Use a simple configuration with one sensor.
    return [
        {
            "channel": 1,
            "scale": 600,
            "offset": 2,
            "calibration": 1,
            "name": "Test Sensor",
            "color": "r",
            "style": "-",
        }
    ]

@pytest.mark.non_gui
def test_sensor_get_reading(sensor_config_test, fake_modbus_client):
    sensor = Sensor(sensor_config_test, fake_modbus_client)
    sensor_values, timestamp = sensor.get_reading()

    assert isinstance(sensor_values, list)
    assert len(sensor_values) == 1

    # Calculation:
    # FakeModbusClient returns 2048.
    # With offset 2: raw_val = 2048 - 2 = 2046.
    # Voltage = (2046 / ADC_MAX) * VOLTAGE_FULL_SCALE ≈ (2046/4095)*10 ≈ 5.0.
    # Processed sensor value = (5.0 / 10) * 600 = 300.
    assert (
        abs(sensor_values[0] - 300) < 5
    ), f"Expected sensor value close to 300, got {sensor_values[0]}"
    assert isinstance(timestamp, float)
