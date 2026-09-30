"""
logger.py
----------
Handles all activity logging for the application.

WHY THIS MODULE EXISTS:
Every security tool must keep an audit trail — a record of what happened
and when. This helps in debugging, and in a real security product, helps
detect suspicious activity (e.g., repeated failed decryption attempts).

We use Python's built-in `logging` module instead of manually writing to
files with `open()`, because `logging`:
  - Automatically adds timestamps
  - Supports different severity levels (INFO, WARNING, ERROR)
  - Is thread-safe and battle-tested
"""

import logging
import os
from datetime import datetime


class ActivityLogger:
    """
    A wrapper class around Python's logging module.

    Using a class (instead of plain functions) lets us:
      - Keep configuration (log file path, formatting) in one place
      - Create ONE logger instance and reuse it across the whole app
      - Easily extend later (e.g., add log rotation, remote logging)
    """

    def __init__(self, log_dir="logs", log_filename="activity.log"):
        """
        Constructor: runs when an ActivityLogger object is created.

        Args:
            log_dir (str): folder where log files are stored.
            log_filename (str): name of the log file.
        """
        # Make sure the logs folder exists; create it if it doesn't.
        # exist_ok=True prevents an error if the folder already exists.
        os.makedirs(log_dir, exist_ok=True)

        # Build the full path to the log file, e.g. "logs/activity.log"
        self.log_path = os.path.join(log_dir, log_filename)

        # Create a dedicated logger object (not the root logger) so that
        # this logger's settings don't interfere with other libraries.
        self.logger = logging.getLogger("SecureFileVaultLogger")
        self.logger.setLevel(logging.INFO)  # Capture INFO and above.

        # Avoid adding duplicate handlers if this class is instantiated
        # more than once (which would cause duplicate log lines).
        if not self.logger.handlers:
            # FileHandler writes log messages to a file on disk.
            file_handler = logging.FileHandler(self.log_path, encoding="utf-8")

            # Formatter defines how each log line looks:
            # timestamp - LEVEL - message
            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler.setFormatter(formatter)

            # Attach the handler to our logger so messages actually get written.
            self.logger.addHandler(file_handler)

    def log_info(self, message: str):
        """Log a normal, successful event (e.g., 'File encrypted successfully')."""
        self.logger.info(message)

    def log_warning(self, message: str):
        """Log something that isn't an error but deserves attention
        (e.g., 'Weak password used')."""
        self.logger.warning(message)

    def log_error(self, message: str):
        """Log a failure (e.g., 'Decryption failed: wrong password')."""
        self.logger.error(message)

    def get_recent_logs(self, n=50):
        """
        Read and return the last `n` lines from the log file.
        Useful for displaying recent activity inside the GUI.

        Args:
            n (int): number of most recent log lines to return.

        Returns:
            list[str]: the last n log lines (or fewer if the file is short).
        """
        if not os.path.exists(self.log_path):
            return []
        with open(self.log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return lines[-n:]  # Slice the last n lines.
