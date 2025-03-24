"""
dialog.py

This module defines the ConfigDialog class, which provides a dialog for
configuring sensors. Users can add, remove, or reset sensor
configurations. Changes are saved persistently using QSettings.
"""

import logging
from itertools import cycle
from typing import Optional, Tuple, List, Dict, Any

from PyQt5.QtCore import QSettings, QRegExp
from PyQt5.QtWidgets import QMessageBox
from PyQt5 import QtWidgets
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QRegExpValidator

from config import save_sensor_config, sensor_config

# Set up a module-level logger.
logger = logging.getLogger(__name__)

# --- Define a list of candidate colors -------
CANDIDATE_COLORS_LIST: List[str] = [
    "red",
    "green",
    "blue",
    "orange",
    "purple",
    "cyan",
    "magenta",
    "brown",
    "pink",
    "gray",
]

CANDIDATE_COLORS = cycle(CANDIDATE_COLORS_LIST)


# -------- Sensor Configuration Dialog --------
class ConfigDialog(QtWidgets.QDialog):
    """
    ConfigDialog provides a GUI for editing the sensor configuration.

    It allows users to view current parameters, add, rem, reset the config
    to default, and save changes. The updated config is saved using QSettings.
    """

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        """
        Initialize the configuration dialog.

        Args:
            parent (QWidget): The parent widget (typically the main window).
        """
        super().__init__(parent)
        self.setWindowTitle("Sensor Configuration")
        self.parent = parent
        self.sensor_entries: List[Dict[str, Any]] = []
        # Store the default sensor configuration from config.py (for reference)
        self.sensor_config: List[Dict[str, Any]] = sensor_config
        # Log the loaded sensor configuration
        logger.debug("Loaded Sensor Config: %s", self.parent.sensor_config)
        self.changes_made: bool = False  # Flag to track if changes were made
        self.initUI()

    def initUI(self) -> None:
        """
        Set up the user interface for the dialog.
        """
        layout = QtWidgets.QVBoxLayout(self)

        # Header layout with labels for each column
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.addWidget(QtWidgets.QLabel("Channel"))
        header_layout.addWidget(QtWidgets.QLabel("Name"))
        header_layout.addWidget(QtWidgets.QLabel("Scale"))
        header_layout.addWidget(QtWidgets.QLabel("Calibration"))
        header_layout.addWidget(QtWidgets.QLabel("Offset"))
        header_layout.addWidget(QtWidgets.QLabel("Color"))
        layout.addLayout(header_layout)

        # Container widget for sensor rows with a vertical layout
        self.sensor_rows_widget = QtWidgets.QWidget()
        self.sensor_rows_layout = QtWidgets.QVBoxLayout(
            self.sensor_rows_widget
        )
        self.sensor_rows_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.sensor_rows_widget)

        # Initialize sensor entries from the parent's configuration
        for i, sensor in enumerate(self.parent.sensor_config):
            self.add_sensor_row(sensor, index=i)

        # Button layout for adding, removing, resetting, and saving changes
        btn_layout = QtWidgets.QHBoxLayout()

        add_btn = QtWidgets.QPushButton("Add Sensor")
        add_btn.clicked.connect(self.add_sensor)
        btn_layout.addWidget(add_btn)

        remove_btn = QtWidgets.QPushButton("Remove Last Sensor")
        remove_btn.clicked.connect(self.remove_sensor)
        btn_layout.addWidget(remove_btn)

        reset_btn = QtWidgets.QPushButton("Default")
        reset_btn.clicked.connect(self.reset_to_default)
        btn_layout.addWidget(reset_btn)

        save_btn = QtWidgets.QPushButton("Save Changes")
        save_btn.clicked.connect(self.save_changes)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def get_unique_color(self) -> str:
        """
        Return a unique color from the color cycle that is not already used
        in the parent's sensor configuration.
        If all candidate colors are used, return the next color in the cycle.
        """
        used_colors = {sensor["color"] for sensor in self.parent.sensor_config}
        # Try one full cycle.
        for _ in range(len(CANDIDATE_COLORS_LIST)):
            color = next(CANDIDATE_COLORS)
            if color not in used_colors:
                return color
        # After candidate colors; fallback to the next color in the cycle.
        return next(CANDIDATE_COLORS)

    def add_sensor_row(
        self, sensor: Dict[str, Any], index: Optional[int] = None
    ) -> None:
        """
        Add a row for a sensor entry in the dialog.

        Args:
            sensor (dict): The sensor configuration dictionary.
            index (int, optional): The index of the sensor in the config. If
        provided, it is used to supply a default channel number if missing.
        """
        row_layout = QtWidgets.QHBoxLayout()

        # Channel: integer from 0 to 64.
        default_channel = sensor.get(
            "channel",
            index + 1 if index is not None else 1
        )
        channel_edit = QtWidgets.QLineEdit(str(default_channel))
        channel_edit.setValidator(QIntValidator(0, 99, self))
        channel_edit.setMaxLength(2)
        row_layout.addWidget(channel_edit)

        # Name: alphanumeric (letters, digits, spaces) up to 16 characters.
        # Set maximum length directly.
        name_edit = QtWidgets.QLineEdit(sensor.get("name", ""))
        name_edit.setMaxLength(16)
        # Use a regular validator: allow letters, digits, and spaces.
        name_validator = QRegExpValidator(QRegExp("[A-Za-z0-9 ]{0,16}"), self)
        name_edit.setValidator(name_validator)
        row_layout.addWidget(name_edit)

        # Scale: positive number (greater than 0).
        scale_edit = QtWidgets.QLineEdit(str(sensor.get("scale", "")))
        # Minimum is a small number; you can adjust the maximum as needed.
        scale_validator = QDoubleValidator(1, 1e9, 2, self)
        scale_validator.setNotation(
            QDoubleValidator.StandardNotation
        )  # Disallow "e" notation.
        scale_edit.setValidator(scale_validator)
        scale_edit.setMaxLength(6)
        # Add tooltip for scale
        scale_edit.setToolTip("Enter the maximum sensor value")
        row_layout.addWidget(scale_edit)

        # Calibration: positive number (greater than 0) with 2 decimal places.
        calib_edit = QtWidgets.QLineEdit(str(sensor.get("calibration", 1)))
        calib_validator = QDoubleValidator(1, 1e9, 2, self)
        calib_validator.setNotation(QDoubleValidator.StandardNotation)
        calib_edit.setValidator(calib_validator)
        calib_edit.setMaxLength(6)
        # Add tooltip for calibration
        calib_edit.setToolTip(
            "Calibration multiplier (e.g., 1.1 = +10% adjustment)"
        )
        row_layout.addWidget(calib_edit)

        # Offset: number greater than or equal to 0 with 2 decimal places
        offset_edit = QtWidgets.QLineEdit(str(sensor.get("offset", 0)))
        offset_validator = QDoubleValidator(0, 1e9, 2, self)
        offset_validator.setNotation(QDoubleValidator.StandardNotation)
        offset_edit.setValidator(offset_validator)
        offset_edit.setMaxLength(6)
        # Add tooltip for offset
        offset_edit.setToolTip(
            "Zero-offset adjustment (To zero the raw input)"
        )
        row_layout.addWidget(offset_edit)

        # Color: no strict validation
        color_edit = QtWidgets.QLineEdit(sensor.get("color", "black"))
        row_layout.addWidget(color_edit)

        # Store the widgets for later retrieval when saving changes
        self.sensor_entries.append(
            {
                "channel": channel_edit,
                "name": name_edit,
                "scale": scale_edit,
                "calibration": calib_edit,
                "offset": offset_edit,
                "color": color_edit,
            }
        )
        self.sensor_rows_layout.addLayout(row_layout)

    def reset_to_default(self) -> None:
        """
        Reset the sensor configuration to the default values.

        This method removes the stored configuration from QSettings and resets
        the parent's configuration, then updates the UI accordingly.
        """
        # Remove saved sensor configuration from QSettings
        settings = QSettings("MyCompany", "HydroPowerSensorPlotter")
        settings.remove("sensor_config")
        # Revert parent's sensor_config to default values
        global sensor_config  # Use the default configuration from config.py
        self.parent.sensor_config = sensor_config.copy()
        # Reset sensor data arrays as well
        self.parent.sensor_data = [[] for _ in self.parent.sensor_config]
        self.parent.full_sensor_data = [[] for _ in self.parent.sensor_config]
        # Reinitialize UI elements that depend on configuration
        self.parent.reinitialize_plot_lines()
        self.parent.refresh_statistics_panel()
        QMessageBox.information(
            self, "Reset", "Configuration has been reset to default."
        )
        # Optionally, close the dialog or refresh the config entries:
        self.accept()

    def add_sensor(self) -> None:
        """
        Add a new sensor to the configuration and update the UI.
        """
        # Get a unique color for the new sensor.
        unique_color = self.get_unique_color()
        sensor = {
            "channel": len(self.parent.sensor_config) + 1,
            "name": f"Sensor {len(self.parent.sensor_config) + 1}",
            "scale": 600,
            "calibration": 1,
            "offset": 2,
            "color": unique_color,
            "style": "-",
        }
        self.parent.sensor_config.append(sensor)
        self.parent.sensor_data.append([])
        self.parent.full_sensor_data.append([])
        # Add the sensor row to the dialog
        # self.add_sensor_row(sensor)  # Use the helper method to add the row
        self.add_sensor_row(sensor, index=len(self.parent.sensor_config) - 1)
        self.sensor_rows_widget.adjustSize()
        self.changes_made = True  # Set flag when a sensor is added

    def remove_sensor(self) -> None:
        """
        Remove the last sensor from the configuration and update the UI.
        """
        if self.parent.sensor_config:
            # Remove the last sensor configuration and corresponding data
            self.parent.sensor_config.pop()
            self.parent.sensor_data.pop()
            self.parent.full_sensor_data.pop()

            # Remove the last row of sensor entry widgets
            if self.sensor_entries:
                last_entry = self.sensor_entries.pop()  # Get the last entry
                for widget in last_entry.values():
                    widget.deleteLater()  # Remove the widgets from the layout

                # Remove the last row layout from the sensor layout
                if self.sensor_rows_layout.count() > 0:
                    item = self.sensor_rows_layout.takeAt(
                        self.sensor_rows_layout.count() - 1
                    )
                    if item and item.layout():
                        item.layout().deleteLater()

            self.changes_made = True  # Set flag when a sensor is removed

    def validate_config(
        self,
        config: List[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        """
        Validate the sensor configuration.

        Args:
            config (list): A list of sensor configuration dictionaries.

        Returns:
            tuple: (is_valid (bool), error_message (str))
        """
        # Check that each sensor has a unique channel number.
        channels = [sensor.get("channel") for sensor in config]
        if len(channels) != len(set(channels)):
            return (
                False,
                (
                    "Duplicate sensor channels found. "
                    "Please ensure each sensor has a unique channel."
                ),
            )

        # Check that scale and calibration values are greater than zero.
        for sensor in config:
            scale = sensor.get("scale", 0)
            calibration = sensor.get("calibration", 1)
            if scale <= 0:
                return (
                    False,
                    f"Scale for sensor '{sensor.get('name', '')}' must be "
                    "greater than zero.",
                )
            if calibration <= 0:
                return (
                    False,
                    f"Calibration for sensor '{sensor.get('name', '')}' must "
                    "be greater than zero.",
                )

        # If all checks pass, configuration is valid.
        return True, ""

    def save_changes(self) -> None:
        """
        Save changes made in the dialog to the parent's sensor configuration.

        The method validates and updates each sensor entry, then persists the
        configuration using QSettings.
        """
        # Initialize the list for auto-correction messages.
        auto_corrected = []
        for i, entry in enumerate(self.sensor_entries):
            # Channel: if conversion fails, default to i+1.
            try:
                self.parent.sensor_config[i]["channel"] = int(
                    entry["channel"].text()
                )
            except ValueError:
                self.parent.sensor_config[i]["channel"] = i + 1

            # Name: store the text as entered.
            self.parent.sensor_config[i]["name"] = entry["name"].text()

            # Scale: must be > 0; if 0 or less, force it to 1.
            try:
                scale_value = float(entry["scale"].text())
                if scale_value < 1:
                    scale_value = 1
                    auto_corrected.append(
                        f"Sensor {i+1} scale auto-corrected to 1."
                    )
                self.parent.sensor_config[i]["scale"] = scale_value
            except ValueError:
                # Use a default value
                self.parent.sensor_config[i]["scale"] = 600

            # Calibration: must be > 0; if 0 or less, force it to 1.
            try:
                calib_value = float(entry["calibration"].text())
                if calib_value < 1:
                    calib_value = 1
                    auto_corrected.append(
                        f"Sensor {i+1} calibration auto-corrected to 1."
                    )
                self.parent.sensor_config[i]["calibration"] = calib_value
            except ValueError:
                self.parent.sensor_config[i]["calibration"] = 1

            # Offset: allowed to be 0 or greater.
            try:
                self.parent.sensor_config[i]["offset"] = float(
                    entry["offset"].text()
                )
            except ValueError:
                self.parent.sensor_config[i]["offset"] = 2

            # Color: store the text.
            self.parent.sensor_config[i]["color"] = entry["color"].text()

        # Inform the user about any auto-corrections.
        if auto_corrected:
            # Display all correction messages in a single dialog.
            QMessageBox.information(
                self,
                "Auto-Correction",
                "\n".join(auto_corrected)
            )

        # --- Additional Validation Step ---
        valid, error_message = self.validate_config(self.parent.sensor_config)
        if not valid:
            QMessageBox.warning(self, "Validation Error", error_message)
            return  # Do not proceed with saving if validation fails.

        # Save the updated configuration persistently.
        save_sensor_config(self.parent.sensor_config)

        # --- Begin Property-Specific UI Updates ---

        # 1. Update sensor object configuration (if applicable).
        if self.parent.sensor is not None:
            self.parent.sensor.sensor_config = self.parent.sensor_config

        # 2. Update line colors and labels directly.
        for idx, sensor in enumerate(self.parent.sensor_config):
            if idx < len(self.parent.lines):
                # Update color if different.
                current_color = self.parent.lines[idx].get_color()
                new_color = sensor["color"]
                if current_color != new_color:
                    self.parent.lines[idx].set_color(new_color)
                # Update label if different.
                current_label = self.parent.lines[idx].get_label()
                new_label = sensor["name"]
                if current_label != new_label:
                    self.parent.lines[idx].set_label(new_label)
        # Update the legend to reflect any label changes.
        self.parent.canvas.ax.legend(loc="upper left")

        # 3. Trigger a plot update to reprocess any numerical changes.
        self.parent.update_plot_ui()

        # --- End Property-Specific UI Updates ---

        if self.changes_made:
            # Reinitialize plots if changes were made.
            self.parent.reinitialize_plot_lines()
            self.changes_made = False  # Reset flag

        # *** Reinitialize the statistics panel ***
        self.parent.init_statistics_panel()
        # Refresh its values afterward.
        self.parent.refresh_statistics_panel()
        self.accept()
