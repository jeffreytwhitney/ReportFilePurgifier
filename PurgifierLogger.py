"""
PurgifierLogger
---------------

Centralized logger factory for the ReportFilePurgifier project.

This module exposes a single function, `get_logger`, which returns a configured
`logging.Logger` instance for a given logger name. Configuration is pulled from
project settings and a file handler is attached to write logs to a consistent
location and format.

Configuration
- Log level is read from the INI configuration via `Utilities.get_stored_ini_value`
  using:
    - section: "Loggers"
    - key: <logger_name>
    - file: "PurgifierSettings"
  If the configured value equals "DEBUG", the logger and file handler operate at
  DEBUG level; otherwise they default to INFO.

- Log file path is resolved using `Utilities.resolve_path()` and logs are written to:
    <resolve_path()>\\PurgifierRunLog.txt

Log format
- %(asctime)s - %(name)s - %(levelname)s - %(message)s

Usage example
--------------
>>> from PurgifierLogger import get_logger
>>> logger = get_logger("CleanupWorker")
>>> logger.info("Cleanup started")
>>> logger.debug("Detailed diagnostics when configured to DEBUG level")

Notes
- Each call to `get_logger` attaches a new `FileHandler` to the named logger.
  Repeated calls with the same `logger_name` in a single process may result in
  duplicated log lines. Prefer calling once per logger name and reusing the
  returned logger (or add a guard to prevent duplicate handlers if needed).
- The log file will be created if it does not exist and appended to otherwise.
- Exceptions may propagate from `Utilities.get_stored_ini_value`, `Utilities.resolve_path`,
  or when the `FileHandler` attempts to open the log file (e.g., permission issues).
"""

import logging

from Utilities import resolve_path, get_stored_ini_value


def get_logger(logger_name) -> logging.Logger:
    """
    Create and return a configured logger for the given name.

    The logger level is determined from the INI configuration under the "Loggers"
    section, with a key matching `logger_name` in the "PurgifierSettings" file.
    When the value is "DEBUG", both the logger and its file handler are set to
    DEBUG; otherwise they default to INFO.

    A `FileHandler` is attached that writes to:
        <resolve_path()>\\PurgifierRunLog.txt
    using the format:
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    Parameters
    ----------
    logger_name : str
        The name of the logger to create or retrieve.

    Returns
    -------
    logging.Logger
        A `logging.Logger` instance configured with level and file handler.

    Side Effects
    ------------
    - Creates or appends to "PurgifierRunLog.txt" under the directory returned
      by `resolve_path()`.
    - Attaches a `FileHandler` to the named logger on each call.

    Possible Exceptions
    -------------------
    - Any exception raised by `get_stored_ini_value` or `resolve_path`.
    - `OSError`/`IOError` when the log file cannot be opened by `FileHandler`.

    Example
    -------
    >>> logger = get_logger("ReportScanner")
    >>> logger.info("Scanning reports...")
    """
    logger = logging.getLogger(logger_name)
    logger_level = get_stored_ini_value("Loggers", logger_name, "PurgifierSettings")
    if logger_level == "DEBUG":
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler(resolve_path() + "\\PurgifierRunLog.txt")
    if logger_level == "DEBUG":
        file_handler.setLevel(logging.DEBUG)
    else:
        file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(file_handler)

    return logger
