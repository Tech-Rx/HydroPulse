"""
ui.py

This module implements the main user interface for HydroPulse.
It sets up the application window, including a toolbar with control buttons,
a plotting area (using Matplotlib embedded in a Qt widget), a statistics panel,
and a status bar that displays real-time connection and process updates.
It also handles Modbus connection management and data saving.

Usage:
    Run this module as the main application window.
"""

# Standard library imports
import os
from collections import deque
from datetime import datetime
import logging

# Third-party imports
import numpy as np
import pandas as pd
from pymodbus.client import ModbusSerialClient as ModbusClient
import serial.tools.list_ports
import mplcursors
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import QThreadPool
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas
)

# Local application imports
from sensor import Sensor, SensorError
from dialog import ConfigDialog
from sensor_worker import SensorWorker
from config import (
    load_sensor_config,
    sensor_config,
    Y_AXIS_MAX,
    TIME_WINDOW_SEC,
    MAX_POINTS,
    POLL_INTERVAL_MS,
)
from save_tasks import SaveTask
from resources import resources_rc  # noqa: F401


# Configure pymodbus logger to suppress warnings
logging.getLogger("pymodbus").setLevel(logging.CRITICAL)
logger = logging.getLogger(__name__)


# -------- Matplotlib Canvas for PyQt --------
class MplCanvas(FigureCanvas):
    """
    MplCanvas embeds a Matplotlib figure into a Qt widget.
    """

    def __init__(
        self,
        parent: QtWidgets.QWidget = None,
        width: int = 8,
        height: int = 6,
        dpi: int = 100,
    ) -> None:
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)
        self.setParent(parent)


# -------- Main Window Class --------
class SensorPlotter(QtWidgets.QMainWindow):
    """
    SensorPlotter is the main window of the HydroPulse application.

    It handles the UI elements including the toolbar, plot area, statistics
    panel,and status bar. It also manages Modbus connections, sensor data
    updates, and data saving.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Hydro Power Sensor Plotter")
        self.setWindowIcon(QtGui.QIcon(":/images/myicon.ico"))
        self.setGeometry(100, 100, 1200, 800)
        # Set global font for a Windows-native look.
        self.setFont(QtGui.QFont("Segoe UI", 10))

        # Load persisted sensor configuration; if none, use the default.
        self.sensor_config = load_sensor_config(sensor_config)

        # For rolling window data, limit to MAX_POINTS entries
        self.sensor_data = [
            deque(maxlen=MAX_POINTS)
            for _ in self.sensor_config
        ]
        self.timestamps = deque(maxlen=MAX_POINTS)

        # For full session data, you may or may not limit; here we don't
        self.full_sensor_data = [deque() for _ in self.sensor_config]
        self.full_timestamps = deque()

        # Create a layout placeholder (if needed for further use)
        self.sensor_layout = QtWidgets.QVBoxLayout()

        # Create and set up the custom status label
        self.status_label = QtWidgets.QLabel()
        self.status_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.status_label.setText(
            "<span style='color: green; font-size: 16px;'>&#9679;</span> "
            "<span style='color: black; font-size: 16px;'>Ready</span>"
        )
        self.status_label.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
        )

        # Initialize modbus client and sensor data storage
        self.modbus_client = None
        self.is_running = False
        self.sensor = None  # New: instance of Sensor
        self.sensor_timer = None  # New: QTimer for periodic readings

        self.last_mouse_event = None

        # Build the UI
        self.initUI()

    def setup_plot_axes(self) -> None:
        """Configure the plot axes with static settings."""
        # Clear the axes to start fresh.
        self.canvas.ax.clear()
        # Set title and labels.
        self.canvas.ax.set_title("Sensor Data")
        self.canvas.ax.set_xlabel("Time (seconds)")
        self.canvas.ax.set_ylabel("Sensor Reading")
        # Set axis limits.
        self.canvas.ax.set_ylim(0, Y_AXIS_MAX)
        self.canvas.ax.set_xlim(0, TIME_WINDOW_SEC)
        # Enable grid and set ticks.
        self.canvas.ax.grid(True)
        self.canvas.ax.set_yticks(np.arange(0, Y_AXIS_MAX + 1, 50))
        self.canvas.ax.set_xticks(np.arange(0, TIME_WINDOW_SEC + 1, 30))

    def initialize_plot_lines(self) -> None:
        """Initialize plot lines for each sensor and add a legend."""
        self.lines = []
        self.scatter_plots = []  # Create a list to hold scatter objects.
        for sensor in self.sensor_config:
            # Use sensor.get("style", "-") in case the style key is missing.
            (line,) = self.canvas.ax.plot(
                [],
                [],
                label=sensor["name"],
                color=sensor["color"],
                linestyle=sensor.get("style", "-"),
                linewidth=2,
            )
            line.set_picker(5)  # Set a 5-pixel picking tolerance.
            self.lines.append(line)

            # Create a scatter plot for individual points.
            scatter_obj = self.canvas.ax.scatter(
                [],
                [],
                color=sensor["color"],
                s=20
            )
            self.scatter_plots.append(scatter_obj)

        self.canvas.ax.legend(loc="upper left")
        self.canvas.draw()

    def initUI(self) -> None:
        """
        Set up the main UI elements including toolbar, plot area, stats panel,
        and status bar.
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
        start_icon.addPixmap(
            QtGui.QPixmap(":/images/start.png"),
            QtGui.QIcon.Mode.Normal,
            QtGui.QIcon.State.Off,
        )
        start_icon.addPixmap(
            QtGui.QPixmap(":/images/start_disabled.png"),
            QtGui.QIcon.Mode.Disabled,
            QtGui.QIcon.State.Off,
        )
        self.start_button = QtWidgets.QPushButton("Start")
        self.start_button.setIcon(start_icon)
        self.start_button.setIconSize(QtCore.QSize(24, 24))
        self.start_button.clicked.connect(self.start_modbus)
        left_layout.addWidget(self.start_button)

        stop_icon = QtGui.QIcon()
        stop_icon.addPixmap(
            QtGui.QPixmap(":/images/stop.png"),
            QtGui.QIcon.Mode.Normal,
            QtGui.QIcon.State.Off,
        )
        stop_icon.addPixmap(
            QtGui.QPixmap(":/images/stop_disabled.png"),
            QtGui.QIcon.Mode.Disabled,
            QtGui.QIcon.State.Off,
        )
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

        # Timer to update COM port list.
        self.com_port_timer = QtCore.QTimer(self)
        self.com_port_timer.timeout.connect(self.update_com_ports)
        self.com_port_timer.start(5000)  # Check every 5 seconds.

        self.baud_rate_combo = QtWidgets.QComboBox()
        baud_rates = [
            "300",
            "1200",
            "2400",
            "4800",
            "9600",
            "19200",
            "38400",
            "57600",
            "115200",
        ]
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
        # Reduce spacing between sensor widgets
        self.stats_layout.setSpacing(2)
        self.init_statistics_panel()

        # Wrap the stats_panel in a QScrollArea so it can scroll.
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidget(self.stats_panel)
        scroll_area.setWidgetResizable(
            True
        )  # Ensures the stats_panel resizes with the scroll area
        scroll_area.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff
        )  # Hide horizontal scroll bar.
        # Remove the frame.
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)

        # Now add the scroll_area to the main layout instead of stats_panel
        main_area.addWidget(scroll_area, 1)

        # Set up the plot axes and initialize plot lines.
        self.setup_plot_axes()
        self.initialize_plot_lines()

        # Add interactive cursor support for the plot
        self.add_cursor()
        self.canvas.mpl_connect("motion_notify_event", self.on_motion_notify)

        # --- Status Bar (Custom One-line Status) ---
        # Create a horizontal layout for the status
        status_layout = QtWidgets.QHBoxLayout()
        # Add 10px bottom padding
        status_layout.setContentsMargins(0, 0, 0, 10)
        # Ensure the label aligns to the left and vertically centered
        self.status_label.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        # Add label to status layout and a stretch so it takes one line.
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        # Add the status layout at the bottom of the main layout
        main_layout.addLayout(status_layout)
        # Initialize the status line as "Ready"
        self.update_status_line_with_default("Ready")

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

    def update_com_ports(self) -> None:
        """
        Automatically update the COM port combo box by rechecking available
        ports. If no COM ports are available, the combo box will be cleared
        and the Start button disabled.
        """
        import serial.tools.list_ports

        ports = list(serial.tools.list_ports.comports())
        port_names = [port.device for port in ports]

        # Get the current items in the combo box.
        current_items = [
            self.com_port_combo.itemText(i)
            for i in range(self.com_port_combo.count())
        ]

        # Only update if there is a change.
        if port_names != current_items:
            self.com_port_combo.clear()
            if port_names:
                self.com_port_combo.addItems(port_names)
                self.com_port_combo.setCurrentIndex(0)
                self.start_button.setEnabled(True)
            else:
                # No ports: the combo box empty and disable Start.
                self.start_button.setEnabled(False)

    def init_statistics_panel(self):
        """Initializes the statistics panel widgets once."""
        self.sensor_stats_labels = {}
        # Clear any existing layout widgets, if needed.
        for i in reversed(range(self.stats_layout.count())):
            widget = self.stats_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

        # Create widgets for each sensor.
        for sensor in self.sensor_config:
            sensor_widget = QtWidgets.QWidget()
            sensor_widget.setFixedHeight(120)
            grid = QtWidgets.QGridLayout(sensor_widget)
            grid.setContentsMargins(5, 5, 5, 5)
            grid.setSpacing(2)

            header = QtWidgets.QLabel(
                f"{sensor['name']} (Ch {sensor.get('channel', '?')})"
            )
            header.setStyleSheet(
                """
                QLabel {
                    font-weight: bold;
                    color: #2c3e50;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 3px;
                }
            """
            )
            grid.addWidget(header, 0, 0, 1, 2)

            # Create static labels and dynamic value labels.
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

            self.stats_layout.addWidget(sensor_widget)
            self.sensor_stats_labels[sensor["name"]] = {
                "current": current_value,
                "min": min_value,
                "max": max_value,
                "avg": avg_value,
            }

        logger.info("Statistics panel initialized")

    def refresh_statistics_panel(self) -> None:
        """
        Rebuild the statistics panel UI to display sensor values.
        """
        # If the panel is not yet initialized, initialize it.
        if not self.sensor_stats_labels:
            self.init_statistics_panel()

        # Update the values for each sensor.
        for idx, sensor in enumerate(self.sensor_config):
            labels = self.sensor_stats_labels.get(sensor["name"])
            if labels:
                data = list(self.sensor_data[idx])
                if data:
                    current_val = data[-1]
                    non_null_data = [d for d in data if d is not None]
                    min_val = min(non_null_data) if non_null_data else None
                    max_val = max(non_null_data) if non_null_data else None
                    avg_val = (
                        (sum(non_null_data) / len(non_null_data))
                        if non_null_data
                        else None
                    )

                    labels["current"].setText(f"{current_val:.2f}")
                    labels["min"].setText(
                        f"{min_val:.2f}" if min_val is not None else ""
                    )
                    labels["max"].setText(
                        f"{max_val:.2f}" if max_val is not None else ""
                    )
                    labels["avg"].setText(
                        f"{avg_val:.2f}" if avg_val is not None else ""
                    )
                else:
                    labels["current"].setText("")
                    labels["min"].setText("")
                    labels["max"].setText("")
                    labels["avg"].setText("")
        # Optionally, log that the panel was updated.
        logger.info("Statistics panel refreshed")

    def add_cursor(self) -> None:
        """
        Enable interactive cursor functionality for the plot.
        """
        if hasattr(self, "cursor"):
            try:
                self.cursor.remove()
            except Exception:
                pass
        self.cursor = mplcursors.cursor(self.lines, hover=True)

        @self.cursor.connect("add")
        def on_add(sel):
            # Set the annotation text based on the target point.
            sel.annotation.set_text(
                f"{sel.artist.get_label()}: {int(round(sel.target[1]))}"
            )
            # Initially, let the annotation be visible.
            sel.annotation.set_visible(True)

    def on_motion_notify(self, event: QtCore.QEvent) -> None:
        self.last_mouse_event = event

        # Check for active selections
        if hasattr(self, "cursor") and self.cursor is not None:
            for sel in self.cursor.selections:
                # Get data coordinates for the target point.
                data_coords = sel.target  # (x, y) in data coordinates
                # Transform them to display (pixel) coordinates.
                display_coords = self.canvas.ax.transData.transform(
                    data_coords
                )
                # Use current event coordinates.
                event_coords = (event.x, event.y)
                # Calculate Euclidean distance in pixels.
                distance = (
                    (display_coords[0] - event_coords[0]) ** 2
                    + (display_coords[1] - event_coords[1]) ** 2
                ) ** 0.5
                threshold = 10  # Adjust this threshold as needed.
                # Show annotation if within threshold, hide otherwise.
                if distance > threshold:
                    sel.annotation.set_visible(False)
                else:
                    sel.annotation.set_visible(True)
            # Force a redraw to update annotation visibility.
            self.canvas.draw_idle()

    def open_config_dialog(self) -> None:
        """
        Open the sensor configuration dialog.
        """
        dialog = ConfigDialog(self)  # Pass sensor_config to the dialog
        dialog.setModal(True)  # Ensure the dialog is non-modal.
        dialog.show()

    def update_status_line_with_default(
        self, state: str, reset_after: int = 3000
    ) -> None:
        self.update_status_line(state, reset_after)

    @QtCore.pyqtSlot(str, int)
    def update_status_line(self, state: str, reset_after: int) -> None:
        # Ensure this method runs on the main (UI) thread.
        if QtCore.QThread.currentThread() != self.thread():
            QtCore.QMetaObject.invokeMethod(
                self,
                "update_status_line",
                QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(str, state),
                QtCore.Q_ARG(int, reset_after)
            )
            return

        # Define error states.
        error_states = {
            "Failed",
            "FileSaveError",
            "FullFileSaveError",
            "Worker Error"}

        # If an error is already, ignore update.
        if (getattr(self, "_error_state_active", False)
                and state not in error_states):
            logger.info("Error state active; ignoring update to %s", state)
            return

        # If the new state is an error...
        if state in error_states:
            # If an error is already active, do not override it.
            if getattr(self, "_error_state_active", False):
                logger.info(
                    "Error state already active; ignoring update to %s",
                    state
                )
                return
            else:
                self._error_state_active = True
                logger.info(
                    "Error state '%s' displayed; auto-reset disabled.",
                    state
                )
                # Use a mapping with unique keys.
                error_map = {
                    "Failed": ("red", "Failed to connect to Modbus"),
                    "FileSaveError": ("red", "File save error"),
                    "FullFileSaveError": ("red", "Full file save error"),
                    "Worker Error": ("red", "Worker error"),
                }
                color, message = error_map.get(state, ("black", state))
                html_text = (
                    f"<span style='color: {color}; font-size: 16px;'>"
                    f"&#9679;</span> "
                    f"<span style='color: black; font-size: 16px;'>"
                    f"{message}</span>"
                )
                self.status_label.setText(html_text)
                return
        else:
            # Clear error state for normal updates.
            self._error_state_active = False

        # Define text and color mapping for each state.
        state_map = {
            "Ready": ("green", "Ready"),
            "Connecting": ("orange", "Connecting..."),
            "Connected": ("green", "Connected to Modbus"),
            "Failed": ("red", "Failed to connect to Modbus"),
            "Disconnected": ("red", "Connection stopped"),
            "FileSaved": ("green", "File saved successfully"),
            "FullFileSaved": ("green", "Full File saved successfully"),
        }
        # Get color and message; default to black if state not defined.
        color, message = state_map.get(state, ("black", state))
        html_text = (
            f"<span style='color: {color}; font-size: 16px;'>&#9679;</span> "
            f"<span style='color: black; font-size: 16px;'>{message}</span>"
        )
        self.status_label.setText(html_text)

        # Schedule auto-reset if applicable.
        delay_mapping = {
            "Connecting": reset_after,
            "Disconnected": reset_after,
            "FileSaved": reset_after,
            "FullFileSaved": reset_after,
        }

        # If this state requires auto-reset.
        if state in delay_mapping:
            delay = delay_mapping[state]
            # Create the timer once if it doesn't exist.
            if not hasattr(self, "_auto_reset_timer"):
                self._auto_reset_timer = QtCore.QTimer(self)
                self._auto_reset_timer.setParent(self)
                self._auto_reset_timer.setSingleShot(True)
                self._auto_reset_timer.timeout.connect(
                    lambda: self.update_status_line("Ready", reset_after)
                )
            # If the timer is active, stop it before starting a new one.
            if self._auto_reset_timer.isActive():
                self._auto_reset_timer.stop()
            self._auto_reset_timer.start(delay)

    def read_sensor_data(self) -> None:
        """
        Called periodically by the sensor_timer to read sensor data and
        update the UI.
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
            self.update_status_line_with_default("Failed")

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

    def reinitialize_plot_lines(self) -> None:
        """
        Reinitialize the plot lines and refresh the statistics panel.

        This clears the current plot, resets data arrays for the current
        window, and redraws the plot lines.
        """
        logger.info("Starting reinitialization of plot lines...")

        # Set up the static plot axes (titles, labels, grid, etc.)
        self.setup_plot_axes()

        # Reinitialize data arrays as deques to maintain the rolling window
        self.sensor_data = [
            deque(maxlen=MAX_POINTS)
            for _ in self.sensor_config
        ]
        self.timestamps = deque(maxlen=MAX_POINTS)

        # Reinitialize full session data as well
        self.full_sensor_data = [deque() for _ in self.sensor_config]
        self.full_timestamps = deque()

        # Initialize the plot lines for each sensor.
        self.initialize_plot_lines()

        # Reattach interactive cursor functionality.
        self.add_cursor()

        # Refresh the statistics panel.
        self.refresh_statistics_panel()

    def start_modbus(self) -> None:
        """
        Establish a Modbus connection using the selected COM port and baud
        rate, and start the sensor reading thread.
        """
        # Force a full disconnect if a modbus client already exists.
        if self.modbus_client:
            self.stop_modbus()
            QtCore.QThread.msleep(1000)

        # Reset error state when attempting a new connection.
        self._error_state_active = False
        if (hasattr(self, "_auto_reset_timer") and
                self._auto_reset_timer.isActive()):
            self._auto_reset_timer.stop()

        if (
            hasattr(self, "sensor_worker")
            and self.sensor_worker is not None
            and self.sensor_worker.isRunning()
        ):
            logger.warning("SensorWorker is already running!")
            return

        try:
            self.update_status_line_with_default("Connecting")
            selected_port = self.com_port_combo.currentText()

            # If the combo box indicates no device available, abort start.
            if "No COM ports available" in selected_port:
                self.update_status_line_with_default("No Device Attached")
                return

            selected_baud = int(self.baud_rate_combo.currentText())
            logger.info(
                "Selected Port: %s, Baud Rate: %s",
                selected_port,
                selected_baud
            )
            self.modbus_client = ModbusClient(
                port=selected_port,
                baudrate=selected_baud,
                bytesize=8,
                parity="N",
                stopbits=1,
                timeout=1,
            )
            if self.modbus_client.connect():
                logger.info("Modbus client connected")
                self.is_running = True
                self.update_status_line_with_default("Connected")
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)

                # Initialize the new Sensor instance
                try:
                    self.sensor = Sensor(
                        self.sensor_config,
                        self.modbus_client
                    )
                except SensorError as e:
                    logger.error("Error initializing sensor: %s", e)
                    self.update_status_line_with_default("Failed")
                    self.is_running = False
                    return

                # Create and start the SensorWorker thread.
                self.sensor_worker = SensorWorker(
                    self.sensor,
                    POLL_INTERVAL_MS,
                    self
                )
                self.sensor_worker.data_ready.connect(self.handle_new_data)
                self.sensor_worker.error_occurred.connect(
                    self.handle_worker_error
                )  # Connect the error signal
                self.sensor_worker.start()
            else:
                self.is_running = False
                self.update_status_line_with_default("Failed")
        except Exception as e:
            logger.error("Error connecting to Modbus: %s", e)
            self.update_status_line_with_default("Failed")
            self.is_running = False

    def handle_worker_error(self, error_message: str) -> None:
        logger.error("SensorWorker Error: %s", error_message)
        self.update_status_line_with_default(f"Worker Error: {error_message}")

    def stop_modbus(self) -> None:
        """
        Stop the sensor reading thread and disconnect from the Modbus client.
        """
        # Stop the sensor worker thread.
        if hasattr(self, "sensor_worker") and self.sensor_worker:
            self.sensor_worker.stop()
            self.sensor_worker = None

        # Optionally disconnect sensor if needed.
        if self.sensor:
            self.sensor.disconnect()
            self.sensor = None

        # Existing code for saving data and closing the modbus client.
        if self.modbus_client:
            # Use QThreadPool to run the save tasks
            QThreadPool.globalInstance().start(SaveTask(self.save_data))
            QThreadPool.globalInstance().start(
                SaveTask(self.save_full_session_data)
            )
            try:
                self.modbus_client.close()
            except Exception:
                pass
            self.modbus_client = None
        self.is_running = False
        self.update_status_line_with_default("Disconnected")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def handle_new_data(
        self, sensor_values: list, current_time: float
    ) -> None:
        """
        Handle new sensor data emitted by the SensorReader thread.

        Appends new sensor values to both the dynamic window and full-session
        arrays, and maintains a rolling window for display.
        """
        # Replace None with 0 (or another value) if desired,
        # or handle them gracefully during calculations.
        sensor_values = [v if v is not None else 0 for v in sensor_values]

        # Ensure sensor_data arrays are at least as long as sensor_values.
        if len(sensor_values) > len(self.sensor_data):
            # Append empty lists for the new channels.
            for _ in range(len(sensor_values) - len(self.sensor_data)):
                self.sensor_data.append(deque(maxlen=MAX_POINTS))
                self.full_sensor_data.append(deque())

        # Append new reading to both dynamic and full-session arrays.
        for idx, value in enumerate(sensor_values):
            self.sensor_data[idx].append(value)
            self.full_sensor_data[idx].append(value)
        self.timestamps.append(current_time)
        self.full_timestamps.append(current_time)

        # Maintain a rolling window of the last TIME_WINDOW_SEC seconds.
        while (
            self.timestamps
            and (current_time - self.timestamps[0]) > TIME_WINDOW_SEC
        ):
            self.timestamps.popleft()
            for idx in range(len(self.sensor_data)):
                if self.sensor_data[idx]:  # Check before popping
                    self.sensor_data[idx].popleft()
                else:
                    logger.warning(
                        "Sensor data deque for index %s is empty.",
                        idx
                    )

        self.update_plot_ui()

    def update_plot_ui(self) -> None:
        """
        Update the plot and stats display based on the current sensor data.
        """
        if not self.timestamps:
            return

        # Convert the deque to a list to support slicing
        timestamps_list = list(self.timestamps)
        # Determine the mini common length among timestamps & all data lists.
        min_len = len(timestamps_list)
        for data_deque in self.sensor_data:
            min_len = min(min_len, len(data_deque))
        if min_len == 0:
            return

        x_data = [t - timestamps_list[0] for t in timestamps_list[:min_len]]

        common_length = min(len(self.lines), len(self.sensor_data))
        for idx in range(common_length):
            y_data = list(self.sensor_data[idx])[:min_len]
            self.lines[idx].set_data(x_data, y_data)
        self.canvas.ax.set_xlim(0, TIME_WINDOW_SEC)
        self.canvas.draw()

        # Update statistics labels for each sensor individually.
        common_length = min(len(self.sensor_config), len(self.sensor_data))
        for idx in range(common_length):
            data = list(self.sensor_data[idx])[:min_len]
            labels = self.sensor_stats_labels.get(
                self.sensor_config[idx]["name"]
            )
            if labels:
                if data:
                    current_val = data[-1]
                    non_null_data = [d for d in data if d is not None]
                    min_val = min(non_null_data) if non_null_data else None
                    max_val = max(non_null_data) if non_null_data else None
                    avg_val = (
                        (sum(non_null_data) / len(non_null_data))
                        if non_null_data
                        else None
                    )
                    labels["current"].setText(
                        f"{current_val:.2f}" if current_val is not None else ""
                    )
                    labels["min"].setText(
                        f"{min_val:.2f}" if min_val is not None else ""
                    )
                    labels["max"].setText(
                        f"{max_val:.2f}" if max_val is not None else ""
                    )
                    labels["avg"].setText(
                        f"{avg_val:.2f}" if avg_val is not None else ""
                    )
                else:
                    labels["current"].setText("")
                    labels["min"].setText("")
                    labels["max"].setText("")
                    labels["avg"].setText("")

    def update_plot(self) -> None:
        """
        (Placeholder method for additional plot updates if needed.)
        """
        pass

    def save_data(self) -> None:
        """
        Save the recent data (in the current rolling window) to an Excel file.
        """
        if not self.timestamps:
            logger.info("No recent data to save.")
            return

        logs_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(logs_dir, exist_ok=True)

        timestamps_list = list(self.timestamps)
        min_len = len(timestamps_list)
        truncated_timestamps = timestamps_list[:min_len]
        data_dict = {
            "Timestamp": [
                datetime.fromtimestamp(ts).strftime("%H:%M:%S")
                for ts in truncated_timestamps
            ]
        }

        for idx, sensor in enumerate(self.sensor_config):
            truncated_data = list(self.sensor_data[idx])[:min_len]
            data_dict[sensor["name"]] = [
                round(x) if x is not None else None for x in truncated_data
            ]

        data_dict = self.pad_dict_list(data_dict)
        df = pd.DataFrame(data_dict)
        file_name = os.path.join(
            logs_dir, f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx"
        )
        try:
            df.to_excel(file_name, index=False)
            logger.info("Recent data saved to %s", file_name)
            self.update_status_line_with_default("FileSaved")
        except Exception as e:
            logger.error("Error saving data to %s: %s", file_name, e)
            self.update_status_line_with_default("FileSaveError")
        # Reset sensor data with new deques.
        self.sensor_data = [
            deque(maxlen=MAX_POINTS)
            for _ in self.sensor_config
        ]
        self.timestamps = deque(maxlen=MAX_POINTS)

    def save_full_session_data(self) -> None:
        """
        Save the full session sensor data to an Excel file.
        """
        if not self.full_timestamps:
            logger.info("No full session data to save.")
            return

        full_dir = os.path.join(os.getcwd(), "logs", "Excel_full")
        os.makedirs(full_dir, exist_ok=True)

        timestamps_full_list = list(self.full_timestamps)
        data_dict = {
            "Timestamp": [
                datetime.fromtimestamp(ts).strftime("%H:%M:%S")
                for ts in timestamps_full_list
            ]
        }

        for idx, sensor in enumerate(self.sensor_config):
            truncated_data = list(self.full_sensor_data[idx])[
                : len(timestamps_full_list)
            ]
            data_dict[sensor["name"]] = [
                round(x) if x is not None else None for x in truncated_data
            ]

        data_dict = self.pad_dict_list(data_dict)
        df = pd.DataFrame(data_dict)
        file_name = os.path.join(
            full_dir,
            f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_full.xlsx"
        )
        try:
            df.to_excel(file_name, index=False)
            logger.info("Full session data saved to %s", file_name)
            self.update_status_line_with_default("FullFileSaved")
        except Exception as e:
            logger.error("Error saving data to %s: %s", file_name, e)
            self.update_status_line_with_default("FullFileSaveError")

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """
        Override the close event to ensure that sensor threads are stopped,
        and data is saved before the application exits.
        """
        # Remove any old reference to sensor_thread if it exists.
        if hasattr(self, "sensor_thread"):
            try:
                self.sensor_thread.stop()
            except Exception:
                pass
            self.sensor_thread = None

        # Stop and clear the sensor worker if it exists.
        if hasattr(self, "sensor_worker") and self.sensor_worker is not None:
            try:
                self.sensor_worker.stop()
            except Exception:
                pass
            self.sensor_worker = None

        # Stop and clear the sensor_timer.
        if hasattr(self, "sensor_timer") and self.sensor_timer is not None:
            if hasattr(self.sensor_timer, "stop"):
                self.sensor_timer.stop()
            self.sensor_timer = None

        # Disconnect and clear the sensor instance.
        if hasattr(self, "sensor") and self.sensor is not None:
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
