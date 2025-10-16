"""
Report File Mover

Overview:
    Moves aging report files from a configured root directory into
    year-based subfolders, helping organize older reports. The intended policy is:
      - For files older than a configured cutoff, move them into a sibling folder
        named "_<YYYY>" based on each file's last-modified year.

Configuration:
    There are two levels of configuration:
      The upper level is the list of report file movers to load from the INI.
      The lower level is the configuration for each mover.

    Values are loaded via `Utilities.get_stored_ini_value(section, key, ini_name)`.
    Expected Values in Upper Level:
        -Section: "ReportFileMovers"
        -Key: "file_movers" (Comma-delimited string of mover names)
    
    Expected Values in Lower Level:
        -Section: "<type>FileMover" example: "MicroVUFileMover"
        -Key: "root_path" (string)
        -Key: "archive_path" (string)
        -Key: "mv_days_to_keep" (int)

Behavior:
    - Scans the configured `root_path` non-recursively.
    - For each file older than the cutoff, creates a year subdirectory (if needed)
      in the same directory with the pattern "_YYYY" and moves the file into it.
    - Logs progress, actions, and any errors encountered.

Logging:
    Uses `PurgifierLogger.get_logger("file_mover_logger")`.
    - DEBUG: start/end, root path, directory creation, and each move.
    - WARNING: recoverable issues (e.g., failure to move a file).
    - ERROR: non-recoverable issues (e.g., unreadable file stats).

Notes and caveats:
    - Traversal is non-recursive; only files directly in `root_path` are processed.
"""
import os
import shutil
from datetime import datetime, timedelta

from Utilities import get_minus_days_beginning_of_day
import PurgifierLogger
from Utilities import get_stored_ini_value


class ReportFileMover:
    """
    Organizes aging MicroVu report files by moving them into year-based folders.

    Initialization:
        - Loads `root_path` and `mv_days_to_keep` from the INI settings.

    Behavior:
        - Determines a time cutoff (expected to be computed and assigned to
          `_pdf_file_cutoff` prior to moving).
        - Scans files within `root_path` (non-recursive).
        - For files older than `_pdf_file_cutoff`, moves them into a subfolder
          named `_<YYYY>` derived from the file's last-modified timestamp.

    Attributes:
        _logger: Logger instance for diagnostics.
        _root_path: Root directory to scan for report files.
        _pdf_file_days_to_keep: Days used to compute age cutoff.
        _pdf_file_cutoff: Datetime boundary; files older than this are moved.
    """
    _logger = None
    _root_path = ""
    _pdf_file_days_to_keep = 0
    _pdf_file_cutoff = None
    _pdf_archive_dir = None

    def __init__(self, mover_type_name: str):
        """
        Initialize the mover by loading configuration and preparing to process files.

        Logs:
            - DEBUG: start message and resolved root path.
            - ERROR: when `root_path` is not configured or `mv_days_to_keep` is invalid.
        """
        self._logger = PurgifierLogger.get_logger("file_mover_logger")
        self._logger.debug("Starting Report File Mover")

        self._root_path = get_stored_ini_value(mover_type_name, "root_path", "PurgifierSettings")
        self._pdf_archive_dir = get_stored_ini_value(mover_type_name, "archive_path", "PurgifierSettings")
        if not self._root_path:
            self._logger.error("Root Path not found in INI file.")
            return

        try:
            self._pdf_file_days_to_keep = int(get_stored_ini_value(mover_type_name, "days_to_keep", "PurgifierSettings"))
            self._pdf_file_cutoff = get_minus_days_beginning_of_day(self._pdf_file_days_to_keep)
        except ValueError:
            self._logger.error("days_to_keep returned either a non-numeric value or else not found in INI file.")
            return

        self._logger.debug(f"Root Path: {self._root_path}")

    def archive_files(self):
        """
        Move files older than the configured cutoff into year-based subfolders.

        Process:
            - Iterate non-recursively through `self._root_path`.
            - For each file, read its modification time.
            - If `mtime` < `_pdf_file_cutoff`, move the file into a folder named
              `_<YYYY>` in the same directory (create if missing).

        Logging:
            - DEBUG: on directory creation, and each successful move.
            - ERROR: if file stats cannot be read.
            - WARNING: if a file cannot be moved.
            - Summary DEBUG: counts of checked and moved files.

        Notes:
            - `_pdf_file_cutoff` must be set prior to calling this method; otherwise,
              the comparison will fail.
            - If only PDF reports should be moved, filter for ".pdf" extension.
        """
        checked = 0
        move_file_count = 0
        errors = 0

        with os.scandir(self._root_path) as entries:
            for entry in entries:
                full_path = os.path.join(self._root_path, entry.name)

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

                if mtime_dt < self._pdf_file_cutoff:
                    try:
                        year_subdir = mtime_dt.strftime("%Y")
                        month_subdir = mtime_dt.strftime("%m-%Y")

                        archive_year_dir = os.path.join(self._pdf_archive_dir, year_subdir)
                        if not os.path.exists(archive_year_dir):
                            self._logger.debug(f"Creating directory: {archive_year_dir}")
                            os.mkdir(archive_year_dir)

                        archive_dir = os.path.join(self._pdf_archive_dir, year_subdir, month_subdir)
                        if not os.path.exists(archive_dir):
                            self._logger.debug(f"Creating directory: {archive_dir}")
                            os.mkdir(archive_dir)
                        archive_path = os.path.join(archive_dir, os.path.basename(full_path))
                        print(archive_path)
                        shutil.move(full_path, archive_path)
                        self._logger.debug(f"Moved: {full_path} to {archive_path}")
                        move_file_count += 1
                    except Exception as e:
                        errors += 1
                        self._logger.warning(f"WARNING: Failed to move file: {full_path} - {e}")

        self._logger.debug(f"Checked: {checked} file(s)")
        self._logger.debug(f"Moved: {move_file_count} .pdf file(s) older than {self._pdf_file_cutoff.strftime("%Y-%m-%d %H:%M:%S")}")

        if errors > 0:
            self._logger.warning(f"WARNING: {errors} error(s) occurred during scanning/deletion.")


if __name__ == "__main__":
    mover = ReportFileMover("MicroVUFileMover")
    mover.archive_files()
