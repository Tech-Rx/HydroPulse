"""
save_tasks.py

This module provides a QRunnable-based task for executing save operations
in a non-blocking manner using PyQt's QThreadPool. It is used to offload heavy
file-saving operations (for example, saving Excel files) to background threads,
keeping the main UI responsive.
"""

from PyQt5.QtCore import QRunnable
import logging
from typing import Callable

# Set up a logger for this module.
logger = logging.getLogger(__name__)


class SaveTask(QRunnable):
    """
    A QRunnable task that executes a save function in a background.

    Attributes:
        save_func (Callable): The function to execute for saving data.

    Usage:
        # Create an instance of SaveTask with your saving function.
        task = SaveTask(save_data_function)
        # Start the task using QThreadPool:
        QThreadPool.globalInstance().start(task)
    """

    def __init__(self, save_func: Callable[[], None]) -> None:
        """
        Initialize the SaveTask.

        Args:
            save_func (Callable): A function that performs the save operation.
            This function should handle all necessary file I/O and must not
            interact with UI elements directly.
        """
        super().__init__()
        self.save_func = save_func

    def run(self):
        """
        Execute the save function. Any exceptions that occur during execution
        are caught and logged.
        """
        try:
            self.save_func()
        except Exception as e:
            logger.error("SaveTask encountered an error: %s", e)
