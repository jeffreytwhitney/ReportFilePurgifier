import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import PurgifierLogger
from Utilities import get_stored_ini_value


def _get_minus_days_beginning_of_month(days: int) -> datetime:
    today = datetime.today()
    thirty_days_ago = today - timedelta(days=days)
    first_day_of_month = (thirty_days_ago.replace(day=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return first_day_of_month


def _get_beginning_of_day(days: int) -> datetime:
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return today - timedelta(days=days)


class CMMRunDataPurgifier:
    _logger = None
    _root_path = ""
    _prg_file_days_to_keep = 0
    _cad_file_days_to_keep = 0
    _cad_file_cutoff = None
    _prg_file_cutoff = None

    def __init__(self):
        self._logger = PurgifierLogger.get_logger("cmm_run_data_purgifier_logger")
        self._logger.debug("Starting CMM Run Data Purge")

        self._root_path = get_stored_ini_value("CMMRunDataPurgifier", "root_path", "Purgifier")
        if not self._root_path:
            self._logger.error("Root Path not found in INI file.")
            return

        if not os.path.exists(self._root_path):
            self._logger.error(f"Path not found: {self._root_path}")
            return

        try:
            self._prg_file_days_to_keep = int(get_stored_ini_value("cmm_prg_days_to_keep", "path", "Purgifier"))
        except ValueError:
            self._logger.error("cmm_prg_days_to_keep returned either a non-numeric value or else not found in INI file.")
            return

        try:
            self._cad_file_days_to_keep = int(get_stored_ini_value("cmm_cad_days_to_keep", "path", "Purgifier"))
        except ValueError:
            self._logger.error("cmm_cad_days_to_keep returned either a non-numeric value or else not found in INI file.")
            return

        self._cad_file_cutoff = _get_beginning_of_day(self._cad_file_days_to_keep)
        self._prg_file_cutoff = _get_minus_days_beginning_of_month(self._prg_file_days_to_keep)

        self._logger.debug(f"Root Path: {self._root_path}")
        self._logger.debug(f"PRG Cutoff Datetime: {self._prg_file_cutoff.strftime("%Y-%m-%d %H:%M:%S")}")
        self._logger.debug(f"CAD Cutoff Datetime: {self._cad_file_cutoff.strftime("%Y-%m-%d %H:%M:%S")}")

    def purge_old_cmm_run_data(self):
        checked = 0
        deleted_prg = 0
        deleted_cad = 0
        errors = 0

        def onerror(err):
            nonlocal errors
            errors += 1
            print(f"WARNING: Failed to access directory: {err}", file=sys.stderr)

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
