# test_file_saving.py
import os
import tempfile
import pytest
import pandas as pd
from ui import SensorPlotter

def test_save_data_creates_excel_file(sensor_plotter, monkeypatch):
    """
    Test that calling save_data() creates an Excel file in the logs directory and resets sensor_data.
    """
    with tempfile.TemporaryDirectory() as tmpdirname:
        monkeypatch.setattr(os, "getcwd", lambda: tmpdirname)
        
        # Setup dummy data.
        sensor_plotter.timestamps = [pd.Timestamp.now().timestamp()]
        sensor_plotter.sensor_data = [[100]]
        sensor_plotter.sensor_config = [{"name": "TestSensor"}]
        
        sensor_plotter.save_data()
        
        logs_dir = os.path.join(tmpdirname, "logs")
        files = os.listdir(logs_dir)
        excel_files = [f for f in files if f.endswith('.xlsx')]
        assert len(excel_files) > 0, "No Excel file created in logs directory."
        
        # After saving, sensor_data should be reset.
        for data in sensor_plotter.sensor_data:
            assert data == [], "sensor_data was not reset after saving."

def test_save_full_session_data_creates_excel_file(sensor_plotter, monkeypatch):
    """
    Test that calling save_full_session_data() creates an Excel file in the full-session logs directory.
    """
    with tempfile.TemporaryDirectory() as tmpdirname:
        monkeypatch.setattr(os, "getcwd", lambda: tmpdirname)
        
        sensor_plotter.full_timestamps = [pd.Timestamp.now().timestamp()]
        sensor_plotter.full_sensor_data = [[200]]
        sensor_plotter.sensor_config = [{"name": "TestSensor"}]
        
        sensor_plotter.save_full_session_data()
        
        full_dir = os.path.join(tmpdirname, "logs", "Excel_full")
        files = os.listdir(full_dir)
        excel_files = [f for f in files if f.endswith('.xlsx')]
        assert len(excel_files) > 0, "No full-session Excel file created."
