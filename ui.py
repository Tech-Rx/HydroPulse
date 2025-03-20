"""
ui.py

This module implements the main user interface for HydroPulse.
It sets up the application window, including a toolbar with control buttons,
a plotting area (using Matplotlib embedded in a Qt widget), a statistics panel, 
and a status bar that displays real-time connection and process updates.
It also handles Modbus connection management and data saving.
"""

import os
import PyQt5.sip as sip
import logging
from datetime import datetime

import numpy as np
import pandas as pd

from pymodbus.client import ModbusSerialClient as ModbusClient
import serial.tools.list_ports

import mplcursors
from PyQt5 import QtCore, QtWidgets, QtGui
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from config import load_sensor_config, sensor_config
from sensor import Sensor, SensorError, POLL_INTERVAL_MS
from dialog import ConfigDialog
from sensor_worker import SensorWorker
import resources_rc

# ================================
# Configuration Constants
# ================================
Y_AXIS_MAX = 1150
TIME_WINDOW_SEC = 300  # 5 minutes
#=================================

# Configure pymodbus logger to suppress warnings
logging.getLogger('pymodbus').setLevel(logging.CRITICAL)
logger = logging.getLogger(__name__)

# -------- Matplotlib Canvas for PyQt --------
class MplCanvas(FigureCanvas):
    """
    MplCanvas embeds a Matplotlib figure into a Qt widget.
    """
    def __init__(self, parent=None, width=8, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)
        self.setParent(parent)

# -------- Main Window Class --------
class SensorPlotter(QtWidgets.QMainWindow):
    """
    SensorPlotter is the main window of the HydroPulse application.
    
    It handles the UI elements including the toolbar, plot area, statistics panel, 
    and status bar. It also manages Modbus connections, sensor data updates, 
    and data saving.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hydro Power Sensor Plotter")
        self.setWindowIcon(QtGui.QIcon(":/images/myicon.ico"))
        self.setGeometry(100, 100, 1200, 800)
        # Set global font for a Windows-native look.
        self.setFont(QtGui.QFont("Segoe UI", 10))

        # Create a layout placeholder (if needed for further use)
        self.sensor_layout = QtWidgets.QVBoxLayout()

        # Create and set up the custom status label
        self.status_label = QtWidgets.QLabel()
        self.status_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.status_label.setText("<span style='color: green; font-size: 16px;'>&#9679;</span> <span style='color: black; font-size: 16px;'>Ready</span>")
        self.status_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)

        # Initialize modbus client and sensor data storage
        self.modbus_client = None
        self.is_running = False
        self.sensor = None          # New: instance of Sensor
        self.sensor_timer = None    # New: QTimer for periodic readings
        
        # Load persisted sensor configuration; if none, use the default.
        self.sensor_config = load_sensor_config(sensor_config)
        self.sensor_data = [[] for _ in self.sensor_config]
        self.timestamps = []
        # full_sensor_data and full_timestamps store all readings from start to stop.
        self.full_sensor_data = [[] for _ in self.sensor_config]
        self.full_timestamps = []
        
        # Build the UI
        self.initUI()
        
    def initUI(self):
        """
        Set up the main UI elements including toolbar, plot area, statistics panel, and status bar.
        """
        central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 0)
        main_layout.setSpacing(10)

        logger.info("UI Initialization started...")
        
        # --- Toolbar (Control Buttons) ---
        toolbar_layout = QtWidgets.QHBoxLayout()
        toolbar_layout.addStretch(0)

        left_layout = QtWidgets.QHBoxLayout()
        start_icon = QtGui.QIcon()
        start_icon.addPixmap(QtGui.QPixmap(":/images/start.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        start_icon.addPixmap(QtGui.QPixmap(":/images/start_disabled.png"), QtGui.QIcon.Mode.Disabled, QtGui.QIcon.State.Off)
        self.start_button = QtWidgets.QPushButton("Start")
        self.start_button.setIcon(start_icon)
        self.start_button.setIconSize(QtCore.QSize(24, 24))
        self.start_button.clicked.connect(self.start_modbus)
        left_layout.addWidget(self.start_button)

        stop_icon = QtGui.QIcon()
        stop_icon.addPixmap(QtGui.QPixmap(":/images/stop.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        stop_icon.addPixmap(QtGui.QPixmap(":/images/stop_disabled.png"), QtGui.QIcon.Mode.Disabled, QtGui.QIcon.State.Off)
        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.setIcon(stop_icon)
        self.stop_button.setIconSize(QtCore.QSize(24, 24))
        self.stop_button.clicked.connect(self.stop_modbus)
        left_layout.addWidget(self.stop_button)
        toolbar_layout.addLayout(left_layout, 1)
        toolbar_layout.addStretch(2)

        center_layout = QtWidgets.QHBoxLayout()
        self.com_port_combo = QtWidgets.QComboBox()
        ports = list(serial.tools.list_ports.comports())
        if ports:
            for port in ports:
                self.com_port_combo.addItem(port.device)
            self.com_port_combo.setCurrentIndex(0)
            self.start_button.setEnabled(True)
        else:
            # No ports found; leave the combo box empty.
            self.start_button.setEnabled(False)
        button_height = self.start_button.sizeHint().height()
        self.com_port_combo.setMinimumHeight(button_height)
        self.com_port_combo.setMinimumWidth(120)
        center_layout.addWidget(self.com_port_combo)

        # Set up a timer to automatically update the COM port list.
        self.com_port_timer = QtCore.QTimer(self)
        self.com_port_timer.timeout.connect(self.update_com_ports)
        self.com_port_timer.start(5000)  # Check every 2 seconds.

        self.baud_rate_combo = QtWidgets.QComboBox()
        baud_rates = ["300", "1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"]
        for rate in baud_rates:
            self.baud_rate_combo.addItem(rate)
        index = self.baud_rate_combo.findText("9600")
        if index != -1:
            self.baud_rate_combo.setCurrentIndex(index)
        self.baud_rate_combo.setMinimumHeight(button_height)
        self.baud_rate_combo.setMinimumWidth(120)
        center_layout.addWidget(self.baud_rate_combo)
        toolbar_layout.addLayout(center_layout, 1)
        toolbar_layout.addStretch(3)

        right_layout = QtWidgets.QHBoxLayout()
        self.config_button = QtWidgets.QPushButton("Configure Sensors")
        self.config_button.setIcon(QtGui.QIcon(":/images/gear.png"))
        self.config_button.setIconSize(QtCore.QSize(24, 24))
        self.config_button.clicked.connect(self.open_config_dialog)
        right_layout.addWidget(self.config_button)
        toolbar_layout.addLayout(right_layout, 1)
        toolbar_layout.addStretch(0)

        # Add the toolbar layout to the main layout
        main_layout.addLayout(toolbar_layout)

        self.com_port_combo.setStyleSheet("")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        # --- Main Area: Plot and Statistics Panel ---
        main_area = QtWidgets.QHBoxLayout()
        main_layout.addLayout(main_area)
        
        # Create and add the Matplotlib canvas for plotting sensor data
        self.canvas = MplCanvas(self, width=10, height=8, dpi=120)
        main_area.addWidget(self.canvas, 10)
        
        # Create and add the statistics panel
        self.stats_panel = QtWidgets.QWidget(self)
        self.stats_layout = QtWidgets.QVBoxLayout(self.stats_panel)
        self.stats_layout.setContentsMargins(0, 0, 0, 0)
        self.stats_layout.setSpacing(2)  # Reduce spacing between sensor widgets
        self.sensor_stats_labels = {}
        self.refresh_statistics_panel()

        # Wrap the stats_panel in a QScrollArea so it can scroll if there are too many sensors.
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidget(self.stats_panel)
        scroll_area.setWidgetResizable(True)  # Ensures the stats_panel resizes with the scroll area
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)  # Hide horizontal scroll bar.
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)  # Remove the frame.
     
        # Now add the scroll_area to the main layout instead of stats_panel
        main_area.addWidget(scroll_area, 1)
        
        # Configure plot axes
        self.canvas.ax.set_title("Sensor Data")
        self.canvas.ax.set_xlabel("Time (seconds)")
        self.canvas.ax.set_ylabel("Sensor Reading")
        self.canvas.ax.set_ylim(0, Y_AXIS_MAX)
        self.canvas.ax.set_xlim(0, TIME_WINDOW_SEC)
        self.canvas.ax.grid(True)
        self.canvas.ax.set_yticks(np.arange(0, Y_AXIS_MAX + 1, 50))
        self.canvas.ax.set_xticks(np.arange(0, TIME_WINDOW_SEC + 1, 30))
        
        # Initialize plot lines for each sensor	
        self.lines = []
        for sensor in self.sensor_config:
            line, = self.canvas.ax.plot([], [], label=sensor["name"],
                                          color=sensor["color"],
                                          linestyle=sensor["style"],
                                          linewidth=2)
            self.lines.append(line)
        self.canvas.ax.legend(loc='upper left')
        self.canvas.draw()

        # Add interactive cursor support for the plot
        self.add_cursor()

        # --- Status Bar (Custom One-line Status) ---
        # Create a horizontal layout for the status
        status_layout = QtWidgets.QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 10)  # Add 10px bottom padding
        # Ensure the label aligns to the left and vertically centered
        self.status_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        # Add the label to the status layout and add a stretch so it takes one line.
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        # Add the status layout at the bottom of the main layout
        main_layout.addLayout(status_layout)
        # Initialize the status line as "Ready"
        self.update_status_line("Ready")

        # Set button styles
        button_style = """
        QPushButton {
            background-color: #0078D7;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            font: 10pt "Segoe UI";
        }
        QPushButton:hover {
            background-color: #005A9E;
        }
        QPushButton:pressed {
            background-color: #004578;
        }
        QPushButton:disabled {
            background-color: #A0A0A0;
            color: #808080;
        }
        """
        self.start_button.setStyleSheet(button_style)
        self.stop_button.setStyleSheet(button_style)
        self.config_button.setStyleSheet(button_style)

        logger.info("UI Initialized")

    def update_com_ports(self):
        """
        Automatically update the COM port combo box by rechecking available ports.
        If no COM ports are available, the combo box will be cleared and the Start button disabled.
        """
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        port_names = [port.device for port in ports]

        # Get the current items in the combo box.
        current_items = [self.com_port_combo.itemText(i) for i in range(self.com_port_combo.count())]

        # Only update if there is a change.
        if port_names != current_items:
            self.com_port_combo.clear()
            if port_names:
                self.com_port_combo.addItems(port_names)
                self.com_port_combo.setCurrentIndex(0)
                self.start_button.setEnabled(True)
            else:
                # No ports available: leave the combo box empty and disable Start.
                self.start_button.setEnabled(False)
        
    def refresh_statistics_panel(self):
        """
        Rebuild the statistics panel UI to display sensor values.
        """
        # Clear the existing widgets in the statistics panel
        for i in reversed(range(self.stats_layout.count())):
            widget = self.stats_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        self.sensor_stats_labels = {}

        # For each sensor, create a widget to display current, min, max, and average values
        for i, sensor in enumerate(self.sensor_config):
            sensor_widget = QtWidgets.QWidget()
            # Set a fixed height to ensure uniformity.
            sensor_widget.setFixedHeight(120) 
            grid = QtWidgets.QGridLayout(sensor_widget)
            grid.setContentsMargins(2, 2, 2, 2)  # Smaller margins
            grid.setSpacing(2)  # Smaller spacing between elements
            header = QtWidgets.QLabel(f"{sensor['name']} (Ch {sensor.get('channel', '?')})")
            header.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    color: #2c3e50;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 3px;
                }
            """)
            grid.addWidget(header, 0, 0, 1, 2)
            current_static = QtWidgets.QLabel("Current:")
            current_value = QtWidgets.QLabel("")
            min_static = QtWidgets.QLabel("Min:")
            min_value = QtWidgets.QLabel("")
            max_static = QtWidgets.QLabel("Max:")
            max_value = QtWidgets.QLabel("")
            avg_static = QtWidgets.QLabel("Avg:")
            avg_value = QtWidgets.QLabel("")
            grid.addWidget(current_static, 1, 0)
            grid.addWidget(current_value, 1, 1)
            grid.addWidget(min_static, 2, 0)
            grid.addWidget(min_value, 2, 1)
            grid.addWidget(max_static, 3, 0)
            grid.addWidget(max_value, 3, 1)
            grid.addWidget(avg_static, 4, 0)
            grid.addWidget(avg_value, 4, 1)
            grid.setContentsMargins(5, 5, 5, 5)
            grid.setSpacing(2)
            self.stats_layout.addWidget(sensor_widget)
            self.sensor_stats_labels[sensor["name"]] = {
                "current": current_value,
                "min": min_value,
                "max": max_value,
                "avg": avg_value
            }

        logger.info("Statistics panel refreshed")

    def add_cursor(self):
        """
        Enable interactive cursor functionality for the plot.
        """
        if hasattr(self, 'cursor'):
            try:
                self.cursor.remove()
            except Exception:
                pass
        self.cursor = mplcursors.cursor(self.lines, hover=True)
        @self.cursor.connect("add")
        def on_add(sel):
            sel.annotation.set_text(f"{sel.artist.get_label()}: {int(round(sel.target[1]))}")
        @self.cursor.connect("remove")
        def on_remove(sel):
            sel.annotation.set_visible(False)

    def open_config_dialog(self):
        """
        Open the sensor configuration dialog.
        """
        dialog = ConfigDialog(self)  # Pass sensor_config to the dialog
        dialog.exec_()  # Open the dialog

    def update_status_line(self, state, reset_after=3000):
        """
        Update the status line with a given state using colored dot icons.
        
        Args:
            state (str): One of "Ready", "Connecting", "Connected", "Failed", 
                         "Disconnected", "FileSaved", or "FileSaveError".
            reset_after (int): Time in milliseconds after which the status resets to "Ready" (default is 3000ms).
        """
        if state == "Ready":
            text = "<span style='color: green; font-size: 16px;'>&#9679;</span> " \
                   "<span style='color: black; font-size: 16px;'>Ready</span>"
        elif state == "Connecting":
            text = "<span style='color: orange; font-size: 16px;'>&#9679;</span> " \
                   "<span style='color: black; font-size: 16px;'>Connecting...</span>"
        elif state == "Connected":
            text = "<span style='color: green; font-size: 16px;'>&#9679;</span> " \
                   "<span style='color: black; font-size: 16px;'>Connected to Modbus</span>"
        elif state == "Failed":
            text = "<span style='color: red; font-size: 16px;'>&#9679;</span> " \
                   "<span style='color: black; font-size: 16px;'>Failed to connect to Modbus</span>"
        elif state == "Disconnected":
            text = "<span style='color: red; font-size: 16px;'>&#9679;</span> " \
                   "<span style='color: black; font-size: 16px;'>Connection stopped</span>"
        elif state == "FileSaved":
            text = "<span style='color: green; font-size: 16px;'>&#9679;</span> " \
                   "<span style='color: black; font-size: 16px;'>File saved successfully</span>"
        elif state == "FileSaveError":
            text = "<span style='color: red; font-size: 16px;'>&#9679;</span> " \
                   "<span style='color: black; font-size: 16px;'>File save error</span>"
        else:
            text = f"<span style='color: black; font-size: 16px;'>{state}</span>"

        # Use sip.isdeleted() to check if self.status_label has been deleted
        if not sip.isdeleted(self.status_label):
            self.status_label.setText(text)
        else:
            # Optionally log or handle the case where the label has been deleted
            logger.warning("Status label has been deleted; update skipped.")

        # Automatically reset to "Ready" after a delay if state is not "Ready"
        if state != "Ready":
            QtCore.QTimer.singleShot(reset_after, lambda: self.update_status_line("Ready", reset_after))

    def read_sensor_data(self):
        """
        Called periodically by the sensor_timer to read sensor data and update the UI.
        """
        if self.sensor is None:
            logger.warning("Sensor is not initialized.")
            return
        try:
            sensor_values, current_time = self.sensor.get_reading()
            self.handle_new_data(sensor_values, current_time)
        except SensorError as e:
            logger.error("Error reading sensor data: %s", e)
            # Optionally, update the status line with an error state.
            self.update_status_line("Failed")

    @staticmethod
    def pad_dict_list(dict_list, pad_value=0):
        """
        Pad lists in a dictionary so that all lists have the same length.
        
        Args:
            dict_list (dict): Dictionary whose values are lists.
            pad_value: Value to pad shorter lists with (default is 0).
        
        Returns:
            dict: The dictionary with padded lists.
        """
        max_length = max(len(lst) for lst in dict_list.values())
        for key, lst in dict_list.items():
            if len(lst) < max_length:
                dict_list[key] += [pad_value] * (max_length - len(lst))
        return dict_list
    
    def reinitialize_plot_lines(self):
        """
        Reinitialize the plot lines and refresh the statistics panel.
        
        This clears the current plot, resets data arrays for the current window, and redraws the plot lines.
        """
        logger.info("Starting reinitialization of plot lines...")
        self.canvas.ax.clear()
        self.canvas.ax.set_title("Sensor Data")
        self.canvas.ax.set_xlabel("Time (seconds)")
        self.canvas.ax.set_ylabel("Sensor Reading")
        self.canvas.ax.set_ylim(0, Y_AXIS_MAX)
        self.canvas.ax.set_xlim(0, TIME_WINDOW_SEC)
        self.canvas.ax.grid(True)
        self.canvas.ax.set_yticks(np.arange(0, Y_AXIS_MAX + 1, 50))
        self.canvas.ax.set_xticks(np.arange(0, TIME_WINDOW_SEC + 1, 30))

        # Clear existing dynamic data arrays
        self.sensor_data = [[] for _ in self.sensor_config]
        self.timestamps = []  # Reset timestamps for the new window

        self.lines = []
        for sensor in self.sensor_config:
            line, = self.canvas.ax.plot([], [], label=sensor["name"],
                                          color=sensor["color"],
                                          linestyle=sensor.get("style", "-"),
                                          linewidth=2)
            self.lines.append(line)
        self.canvas.ax.legend(loc='upper left')
        self.canvas.draw()

        self.add_cursor()
        self.refresh_statistics_panel()

    def start_modbus(self):
        """
        Establish a Modbus connection using the selected COM port and baud rate,
        and start the sensor reading thread.
        """
        try:
            self.update_status_line("Connecting")
            selected_port = self.com_port_combo.currentText()
        
            # If the combo box indicates no device available, abort start.
            if "No COM ports available" in selected_port:
                self.update_status_line("No Device Attached")
                return

            selected_baud = int(self.baud_rate_combo.currentText())
            logger.info("Selected Port: %s, Baud Rate: %s", selected_port, selected_baud)
            self.modbus_client = ModbusClient(
                port=selected_port,
                baudrate=selected_baud,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=1
            )
            if self.modbus_client.connect():
                logger.info("Modbus client connected")
                self.is_running = True
                self.update_status_line("Connected")
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)

                # Initialize the new Sensor instance
                try:
                    self.sensor = Sensor(self.sensor_config, self.modbus_client)
                except SensorError as e:
                    logger.error("Error initializing sensor: %s", e)
                    self.update_status_line("Failed")
                    self.is_running = False
                    return

                # Create and start the SensorWorker thread.
                self.sensor_worker = SensorWorker(self.sensor, POLL_INTERVAL_MS, self)
                self.sensor_worker.data_ready.connect(self.handle_new_data)
                self.sensor_worker.start()
            else:
                self.is_running = False
                self.update_status_line("Failed")
        except Exception as e:
            logger.error("Error connecting to Modbus: %s", e)
            self.update_status_line("Failed")
            self.is_running = False
        
    def stop_modbus(self):
        """
        Stop the sensor reading thread and disconnect from the Modbus client.
        """
        # Stop the sensor worker thread.
        if hasattr(self, 'sensor_worker') and self.sensor_worker:
            self.sensor_worker.stop()
            self.sensor_worker = None

        # Optionally disconnect sensor if needed.
        if self.sensor:
            self.sensor.disconnect()
            self.sensor = None

        # Existing code for saving data and closing the modbus client.
        if self.modbus_client:
            self.save_data()
            self.save_full_session_data()
            try:
                self.modbus_client.close()
            except Exception:
                pass
            self.modbus_client = None
        self.is_running = False
        self.update_status_line("Disconnected")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
    def handle_new_data(self, sensor_values, current_time):
        """
        Handle new sensor data emitted by the SensorReader thread.
        
        Appends new sensor values to both the dynamic window and full-session arrays,
        and maintains a rolling window for display.
        """
        # Append new reading to both dynamic and full-session arrays.
        for idx, value in enumerate(sensor_values):
            self.sensor_data[idx].append(value)
            self.full_sensor_data[idx].append(value)
        self.timestamps.append(current_time)
        self.full_timestamps.append(current_time)
        
        # Maintain a rolling window of the last TIME_WINDOW_SEC seconds.
        while self.timestamps and (current_time - self.timestamps[0]) > TIME_WINDOW_SEC:
            self.timestamps.pop(0)
            for idx in range(len(self.sensor_data)):
                if self.sensor_data[idx]:  # Check before popping
                    self.sensor_data[idx].pop(0)
                else:
                    logger.warning("Sensor data list for index %s is empty.", idx)
        self.update_plot_ui()
        
    def update_plot_ui(self):
        """
        Update the plot and statistics display based on the current sensor data.
        """
        if not self.timestamps:
            return

        # Determine the minimum common length among timestamps and all sensor data lists.
        min_len = len(self.timestamps)
        for data_list in self.sensor_data:
            min_len = min(min_len, len(data_list))
        if min_len == 0:
            return

        x_data = [t - self.timestamps[0] for t in self.timestamps[:min_len]]
        for idx, line in enumerate(self.lines):
            y_data = self.sensor_data[idx][:min_len]
            line.set_data(x_data, y_data)
        self.canvas.ax.set_xlim(0, TIME_WINDOW_SEC)
        self.canvas.draw()
        
        # Update statistics labels for each sensor individually.
        for idx, sensor in enumerate(self.sensor_config):
            data = self.sensor_data[idx][:min_len]
            labels = self.sensor_stats_labels.get(sensor["name"])
            if labels:
                if data:
                    current_val = data[-1]
                    non_null_data = [d for d in data if d is not None]
                    min_val = min(non_null_data) if non_null_data else None
                    max_val = max(non_null_data) if non_null_data else None
                    avg_val = (sum(non_null_data) / len(non_null_data)) if non_null_data else None
                    labels["current"].setText(f"{current_val:.2f}" if current_val is not None else "")
                    labels["min"].setText(f"{min_val:.2f}" if min_val is not None else "")
                    labels["max"].setText(f"{max_val:.2f}" if max_val is not None else "")
                    labels["avg"].setText(f"{avg_val:.2f}" if avg_val is not None else "")
                else:
                    labels["current"].setText("")
                    labels["min"].setText("")
                    labels["max"].setText("")
                    labels["avg"].setText("")

    def update_plot(self):
        """
        (Placeholder method for additional plot updates if needed.)
        """
        pass
        
    def save_data(self):
        """
        Save the recent sensor data (within the current rolling window) to an Excel file.
        """
        if not self.timestamps:
            logger.info("No recent data to save.")
            return

        logs_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(logs_dir, exist_ok=True)

        min_len = len(self.timestamps)
        truncated_timestamps = self.timestamps[:min_len]
        data_dict = {"Timestamp": [datetime.fromtimestamp(ts).strftime("%H:%M:%S") for ts in truncated_timestamps]}
        for idx, sensor in enumerate(self.sensor_config):
            truncated_data = self.sensor_data[idx][:min_len]
            data_dict[sensor["name"]] = [round(x) if x is not None else None for x in truncated_data]

        data_dict = self.pad_dict_list(data_dict)
        df = pd.DataFrame(data_dict)
        file_name = os.path.join(logs_dir, f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx")
        try:
            df.to_excel(file_name, index=False)
            logger.info("Recent data saved to %s", file_name)
            self.update_status_line("FileSaved")
        except Exception as e:
            logger.error("Error saving data to %s: %s", file_name, e)
            self.update_status_line("FileSaveError")
        self.sensor_data = [[] for _ in self.sensor_config]
        self.timestamps = []
        
    def save_full_session_data(self):
        """
        Save the full session sensor data to an Excel file.
        """
        if not self.full_timestamps:
            logger.info("No full session data to save.")
            return

        full_dir = os.path.join(os.getcwd(), "logs", "Excel_full")
        os.makedirs(full_dir, exist_ok=True)

        data_dict = {"Timestamp": [datetime.fromtimestamp(ts).strftime("%H:%M:%S") for ts in self.full_timestamps]}
        for idx, sensor in enumerate(self.sensor_config):
            truncated_data = self.full_sensor_data[idx][:len(self.full_timestamps)]
            data_dict[sensor["name"]] = [round(x) if x is not None else None for x in truncated_data]

        data_dict = self.pad_dict_list(data_dict)
        df = pd.DataFrame(data_dict)
        file_name = os.path.join(full_dir, f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_full.xlsx")
        try:
            df.to_excel(file_name, index=False)
            logger.info("Full session data saved to %s", file_name)
            self.update_status_line("FileSaved")
        except Exception as e:
            logger.error("Error saving data to %s: %s", file_name, e)
            self.update_status_line("FileSaveError")

    def closeEvent(self, event):
        """
        Override the close event to ensure that sensor threads are stopped,
        and data is saved before the application exits.
        """    
        # Remove any old reference to sensor_thread if it exists.
        if hasattr(self, 'sensor_thread'):
            try:
                self.sensor_thread.stop()
            except Exception:
                pass
            self.sensor_thread = None

        # Stop and clear the sensor worker if it exists.
        if hasattr(self, 'sensor_worker') and self.sensor_worker is not None:
            try:
                self.sensor_worker.stop()
            except Exception:
                pass
            self.sensor_worker = None

        # Stop and clear the sensor_timer.
        if hasattr(self, 'sensor_timer') and self.sensor_timer is not None:
            if hasattr(self.sensor_timer, 'stop'):
                self.sensor_timer.stop()
            self.sensor_timer = None

        # Disconnect and clear the sensor instance.
        if hasattr(self, 'sensor') and self.sensor is not None:
            try:
                self.sensor.disconnect()
            except Exception:
                pass
            self.sensor = None

        # Save data and disconnect modbus client.
        if self.modbus_client:
            self.save_data()  # Save the last 5 minutes of data
            self.save_full_session_data()  # Save all session data
            try:
                self.modbus_client.close()
            except Exception:
                pass
            self.modbus_client = None

        event.accept()
