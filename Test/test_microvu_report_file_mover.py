from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest

import ReportFileMover


@pytest.fixture
def mv_ini_values():
    return {
        ("MicroVUFileMover", "root_path", "PurgifierSettings"):    "S:\\Micro-Vu",
        ("MicroVUFileMover", "archive_path", "PurgifierSettings"): "S:\\Micro-Vu\\Archives",
        ("MicroVUFileMover", "days_to_keep", "PurgifierSettings"): "30",
    }


def mock_get_mv_stored_ini_value(section, key, ini_name):
    values = {
        ("MicroVUFileMover", "root_path", "PurgifierSettings"):    "S:\\Micro-Vu",
        ("MicroVUFileMover", "archive_path", "PurgifierSettings"): "S:\\Micro-Vu\\Archives",
        ("MicroVUFileMover", "days_to_keep", "PurgifierSettings"): "30",
    }
    return values.get((section, key, ini_name), "")


@patch("ReportFileMover.get_stored_ini_value", side_effect=mock_get_mv_stored_ini_value)
@patch("ReportFileMover.PurgifierLogger.get_logger")
def test_init_loads_config(mock_logger, mock_ini):
    logger = MagicMock()
    mock_logger.return_value = logger
    mover = ReportFileMover.ReportFileMover("MicroVUFileMover")
    assert mover._root_path == "S:\\Micro-Vu"
    assert mover._pdf_archive_dir == "S:\\Micro-Vu\\Archives"
    assert mover._pdf_file_days_to_keep == 30
    assert isinstance(mover._pdf_file_cutoff, datetime)
    logger.debug.assert_any_call("Starting Report File Mover")
    logger.debug.assert_any_call("Root Path: S:\\Micro-Vu")


@patch("ReportFileMover.get_stored_ini_value", side_effect=mock_get_mv_stored_ini_value)
@patch("ReportFileMover.PurgifierLogger.get_logger")
@patch("ReportFileMover.os")
@patch("ReportFileMover.shutil.move")
def test_archive_files_moves_old_files(mock_move, mock_os, mock_logger, mock_ini):
    logger = MagicMock()
    mock_logger.return_value = logger
    mover = ReportFileMover.ReportFileMover("MicroVUFileMover")
    # Setup fake files
    entry_old = MagicMock()
    entry_old.is_file.return_value = True
    entry_old.name = "old_report.pdf"
    entry_new = MagicMock()
    entry_new.is_file.return_value = True
    entry_new.name = "new_report.pdf"
    mock_os.scandir.return_value.__enter__.return_value = [entry_old, entry_new]
    # Old file: older than cutoff
    old_mtime = (datetime.today() - timedelta(days=40)).timestamp()
    new_mtime = (datetime.today() - timedelta(days=10)).timestamp()

    def getmtime_side_effect(path):
        if "old_report.pdf" in path:
            return old_mtime
        else:
            return new_mtime

    mock_os.path.getmtime.side_effect = getmtime_side_effect
    mock_os.path.exists.return_value = False
    mock_os.path.join.side_effect = lambda *args: "\\".join(args)
    mock_os.mkdir = MagicMock()
    # Run
    mover.archive_files()
    # Old file should be moved
    assert mock_move.call_count == 1
    logger.debug.assert_any_call("Moved: S:\\Micro-Vu\\old_report.pdf to S:\\Micro-Vu\\Archives\\<YEAR>\\<MONTH-YEAR>\\old_report.pdf".replace("<YEAR>", (
            datetime.today() - timedelta(days=40)).strftime("%Y")).replace("<MONTH-YEAR>", (datetime.today() - timedelta(days=40)).strftime("%m-%Y")))


@patch("ReportFileMover.get_stored_ini_value", side_effect=mock_get_mv_stored_ini_value)
@patch("ReportFileMover.PurgifierLogger.get_logger")
def test_init_invalid_days_to_keep_logs_error(mock_logger, mock_ini):
    logger = MagicMock()
    mock_logger.return_value = logger

    def bad_ini(section, key, ini_name):
        if key == "days_to_keep":
            return "not_a_number"
        return mock_get_mv_stored_ini_value(section, key, ini_name)

    with patch("ReportFileMover.get_stored_ini_value", side_effect=bad_ini):
        mover = ReportFileMover.ReportFileMover("MicroVUFileMover")
        logger.error.assert_any_call("days_to_keep returned either a non-numeric value or else not found in INI file.")
