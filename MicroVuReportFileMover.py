import os
import shutil
from datetime import datetime, timedelta

import PurgifierLogger
from Utilities import get_stored_ini_value


def _get_minus_days_beginning_of_month(days: int) -> datetime:
    today = datetime.today()
    thirty_days_ago = today - timedelta(days=days)
    first_day_of_month = (thirty_days_ago.replace(day=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return first_day_of_month


class MicroVuReportFileMover:
    _logger = None
    _root_path = ""
    _pdf_file_days_to_keep = 0
    _pdf_file_cutoff = None

    def __init__(self):
        self._logger = PurgifierLogger.get_logger("micro_vu_file_mover_logger")
        self._logger.debug("Starting MicroVu Report File Mover")

        self._root_path = get_stored_ini_value("MicroVUFileMover", "root_path", "PurgifierSettings")
        if not self._root_path:
            self._logger.error("Root Path not found in INI file.")
            return

        try:
            self._pdf_file_days_to_keep = int(get_stored_ini_value("MicroVUFileMover", "mv_days_to_keep", "PurgifierSettings"))
        except ValueError:
            self._logger.error("mv_days_to_keep returned either a non-numeric value or else not found in INI file.")
            return

        self._logger.debug(f"Root Path: {self._root_path}")

    def move_microvu_files(self):
        checked = 0
        move_file_count = 0
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

                if mtime_dt < self._pdf_file_cutoff:
                    try:
                        year_subdir = "_" + mtime_dt.strftime("%Y")
                        new_dir = os.path.join(os.path.dirname(full_path), year_subdir)
                        if not os.path.exists(new_dir):
                            self._logger.debug(f"Creating directory: {new_dir}")
                            os.mkdir(new_dir)
                        new_path = os.path.join(new_dir, os.path.basename(full_path))
                        shutil.move(full_path, new_path)
                        self._logger.debug(f"Moved: {full_path} to {new_path}")
                        move_file_count += 1
                    except Exception as e:
                        errors += 1
                        self._logger.warning(f"WARNING: Failed to move file: {full_path} - {e}")

        self._logger.debug(f"Checked: {checked} file(s)")
        self._logger.debug(f"Moved: {move_file_count} .pdf file(s) older than {self._pdf_file_cutoff.strftime("%Y-%m-%d %H:%M:%S")}")

        if errors > 0:
            self._logger.warning(f"WARNING: {errors} error(s) occurred during scanning/deletion.")
