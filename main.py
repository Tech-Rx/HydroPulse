"""
main.py

Entry point for the HydroPulse application.

This module initializes the QApplication, sets the global style and font, and launches the main window (SensorPlotter).
It also configures logging so that application events are recorded.
"""

import logging
import sys
from PyQt5 import QtWidgets, QtGui
from ui import SensorPlotter
from logging.handlers import RotatingFileHandler
import resources_rc # Ensure the resources are loaded

# Configure logging
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

# File handler with rotation (max 1MB per file, keep last 3 files)
file_handler = RotatingFileHandler("hydropulse.log", maxBytes=1_000_000, backupCount=3)
file_handler.setFormatter(log_formatter)

logging.basicConfig(level=logging.INFO, handlers=[console_handler, file_handler])

logger = logging.getLogger("HydroPulse")
logger.info("Starting HydroPulse application...")

# Handle unexpected exceptions
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("WindowsVista")
    app.setFont(QtGui.QFont("Segoe UI", 10))
    window = SensorPlotter()
    window.showMaximized()
    sys.exit(app.exec_())
