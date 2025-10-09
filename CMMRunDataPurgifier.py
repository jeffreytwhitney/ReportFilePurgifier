"""
CMM Run Data Purgifier

Overview:
    This module purges legacy CMM run data files from a configured root directory
    based on two retention policies:
      - General PRG files are deleted if their last-modified timestamp is older
        than x days. So if x=30, the cutoff is 30 days ago from today's date.
      - CAD files (i.e., files with the .CAD extension, case-insensitive) are
        deleted if their last-modified timestamp is older than N days (midnight).
        So if N=1 and today is 2025-09-27, the cutoff is 2025-09-26 00:00:00.

        Originally, the script that I.T. had deleted every cad file older that a certain number of hours,
        but I only want to run this thing once a day, and I don't want the CAD file to delete if you run it
        at 11:59 PM, and then you go looking for the CAD file at 12:05 AM, and it's not there because
        it deleted everything from yesterday...I can see that possibly causing issues.

    All actions and anomalies are logged via the configured logger.

Configuration:
    Values are loaded via `Utilities.get_stored_ini_value(section, key, ini_name)`.

    Expected INI entries (illustrative; align with your actual INI schema):
      - Section: "CMMRunDataPurgifier"
          - Key: "root_path" (string) - Root directory containing files to purge.
          - Key: "<prg_days_key>" (int) - Number of days used to compute PRG cutoff.
          - Key: "<cad_days_key>" (int) - Number of days used to compute CAD cutoff.
      - Ini name: "PurgifierSettings"

    Note: The function calls currently use the keys/sections exactly as coded in
    `__init__`. Ensure your INI matches those expectations or adjust the code/INI
    accordingly.

Usage:
    Instantiate and invoke the purge:
        >>> purgifier = CMMRunDataPurgifier()
        >>> purgifier.purge_old_cmm_run_data()

Logging:
    Uses `PurgifierLogger.get_logger("cmm_run_data_purgifier_logger")`.
    Emits debug logs for decisions and warnings for recoverable errors.

Caveats:
    - Only files directly under the configured root directory are considered
      (no recursive traversal of subdirectories).
    - Files are filtered by extension for CAD logic (".CAD", case-insensitive)
      but PRG logic applies to all files (based on date).
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

import PurgifierLogger
from Utilities import get_stored_ini_value


def _get_minus_days_date(days: int) -> datetime:
    """
    Returns date x days ago.

    Args:
        days: Number of days to subtract from today.

    Returns:
        A `datetime` at 00:00:00 representing the date x days ago.
    """
    today = datetime.today()
    date_minus_days = today - timedelta(days=days)
    return date_minus_days


def _get_beginning_of_day(days: int) -> datetime:
    """
    Compute the midnight boundary for "today - days".

    Args:
        days: Number of days to subtract from today.

    Returns:
        A `datetime` at 00:00:00 for the computed day.
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return today - timedelta(days=days)


class CMMRunDataPurgifier:
    """
    Purges CMM run data files based on configured retention windows.

    Behavior:
        - Determines two cutoff datetimes:
            1) PRG cutoff: beginning of the month for (today - prg_days_to_keep).
            2) CAD cutoff: beginning of the day for (today - cad_days_to_keep).
        - Scans the configured root directory (non-recursive).
        - Deletes:
            - Any file older than the PRG cutoff.
            - Any ".CAD" file older than the CAD cutoff.
        - Logs the counts of checked, deleted (PRG/CAD), and errors.

    Initialization:
        Loads configuration from the INI via `get_stored_ini_value`. If any required
        value is missing or invalid, an error is logged and the instance initializes
        with no effective purge (since paths/durations are absent).

    Attributes:
        _logger: Module logger instance.
        _root_path: The root directory to scan, from INI.
        _prg_file_days_to_keep: Integer days to compute PRG cutoff.
        _cad_file_days_to_keep: Integer days to compute CAD cutoff.
        _cad_file_cutoff: Computed CAD cutoff `datetime`.
        _prg_file_cutoff: Computed PRG cutoff `datetime`.
    """
    _logger = None
    _root_path = ""
    _prg_file_days_to_keep = 0
    _cad_file_days_to_keep = 0
    _cad_file_cutoff = None
    _prg_file_cutoff = None

    def __init__(self):
        """
        Initialize the purgifier by loading configuration and computing cutoffs.

        Logs:
            - Errors if the root path is missing, does not exist, or duration values
              are non-numeric/missing.
            - Debug entries for root path and computed cutoff timestamps.
        """
        self._logger = PurgifierLogger.get_logger("cmm_run_data_purgifier_logger")
        self._logger.debug("Starting CMM Run Data Purge")

        self._root_path = get_stored_ini_value("CMMRunDataPurgifier", "root_path", "PurgifierSettings")
        if not self._root_path:
            self._logger.error("Root Path not found in INI file.")
            return

        if not os.path.exists(self._root_path):
            self._logger.error(f"Path not found: {self._root_path}")
            return

        try:
            self._prg_file_days_to_keep = int(get_stored_ini_value("CMMRunDataPurgifier", "path", "PurgifierSettings"))
        except ValueError:
            self._logger.error("cmm_prg_days_to_keep returned either a non-numeric value or else not found in INI file.")
            return

        try:
            self._cad_file_days_to_keep = int(get_stored_ini_value("cmm_cad_days_to_keep", "path", "PurgifierSettings"))
        except ValueError:
            self._logger.error("cmm_cad_days_to_keep returned either a non-numeric value or else not found in INI file.")
            return

        self._cad_file_cutoff = _get_beginning_of_day(self._cad_file_days_to_keep)
        self._prg_file_cutoff = _get_minus_days_date(self._prg_file_days_to_keep)

        self._logger.debug(f"Root Path: {self._root_path}")
        self._logger.debug(f"PRG Cutoff Datetime: {self._prg_file_cutoff.strftime("%Y-%m-%d %H:%M:%S")}")
        self._logger.debug(f"CAD Cutoff Datetime: {self._cad_file_cutoff.strftime("%Y-%m-%d %H:%M:%S")}")

    def purge_old_cmm_run_data(self):
        """
        Scan the root directory and purge files based on cutoff policies.

        Deletion rules:
            - If file mtime < PRG cutoff: delete (any extension).
            - If file extension is ".CAD" (case-insensitive) and mtime < CAD cutoff: delete.

        Logging:
            - Debug for each successful deletion.
            - Warning for individual deletion failures and summary if any errors occurred.
            - Summary of checked, deleted (PRG/CAD), and error counts.

        Notes:
            - Uses non-recursive `os.scandir` over the configured `_root_path`.
            - The PRG rule applies to all files; the CAD rule applies only to ".CAD".
              A CAD file may be deleted under either rule when applicable.
            - The reason I'm using os.scandir here is because it is a MASSIVE subdirectory filled with thousands
              of files. I can't use any form of file enumeration where you load the contents into memory first. 
              That takes forever and it a terrible use of resources.
        """
        checked = 0
        deleted_prg = 0
        deleted_cad = 0
        errors = 0

        with os.scandir(self._root_path) as entries:
            for entry in entries:
                full_path = os.path.join(self._root_path, entry)
                if not entry.is_file():
                    continue
                checked += 1

                try:
                    mtime = os.path.getmtime(full_path)
                    mtime_dt = datetime.fromtimestamp(mtime)
                except Exception as e:
                    errors += 1
                    self._logger.error(f"Failed to get file stats for file: {full_path}")
                    continue

                if mtime_dt < self._prg_file_cutoff:
                    try:
                        os.remove(full_path)
                        self._logger.debug(f"Deleted: {full_path}")
                        deleted_prg += 1
                    except Exception as e:
                        errors += 1
                        self._logger.warning(f"WARNING: Failed to delete: {full_path} - {e}")

                extension = Path(full_path).suffix.upper()
                if extension == ".CAD" and mtime_dt < self._cad_file_cutoff:
                    try:
                        os.remove(full_path)
                        self._logger.debug(f"Deleted: {full_path}")
                        deleted_cad += 1
                    except Exception as e:
                        errors += 1
                        self._logger.warning(f"WARNING: Failed to delete: {full_path} - {e}")

        self._logger.debug(f"Checked: {checked} file(s)")
        self._logger.debug(f"Deleted PRG files: {deleted_prg} file(s) older than {self._prg_file_cutoff.strftime("%Y-%m-%d %H:%M:%S")}")
        self._logger.debug(f"Deleted CAD files: {deleted_cad} file(s) older than {self._cad_file_cutoff.strftime("%Y-%m-%d %H:%M:%S")}")
        if errors > 0:
            self._logger.warning(f"WARNING: {errors} error(s) occurred during scanning/deletion.")