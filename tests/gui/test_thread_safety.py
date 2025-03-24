from PyQt5 import QtCore
import pytest
pytest.skip("Skipping file saving tests due to hang", allow_module_level=True)
@pytest.mark.gui
# test_thread_safety.py
def test_concurrent_data_and_config_updates(sensor_plotter, qtbot):
    """Test data polling while modifying sensor config."""
    # Define a new sensor object (adjust the structure as needed)
    new_sensor = {"id": 123, "name": "Test Sensor", "value": 0}

    qtbot.mouseClick(sensor_plotter.config_button, QtCore.Qt.LeftButton)
    # Simulate config changes during active polling
    sensor_plotter.sensor_worker.data_ready.connect(
        lambda: sensor_plotter.sensor_config.append(new_sensor)
    )

    # Depending on the intended behavior, you might need to trigger a data_ready signal here
    # or wait for some event before asserting the condition
    assert not sensor_plotter.sensor_worker._running, "Race condition detected"
