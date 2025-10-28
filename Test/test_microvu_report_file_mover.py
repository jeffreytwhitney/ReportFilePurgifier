import os
import shutil
from datetime import datetime, timedelta, time
from types import SimpleNamespace
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
    mock_os.path.basename.side_effect = lambda path: path.split("\\")[-1]
    mock_os.mkdir = MagicMock()
    # Run
    mover.archive_files()
    # Old file should be moved
    assert mock_move.call_count == 1
    logger.debug.assert_any_call("Moved: S:\\Micro-Vu\\old_report.pdf to S:\\Micro-Vu\\Archives\\<YEAR>\\<MONTH-YEAR>\\old_report.pdf".replace("<YEAR>", (
            datetime.today() - timedelta(days=40)).strftime("%Y")).replace("<MONTH-YEAR>", (
                datetime.today() - timedelta(days=40)).strftime("%m-%Y")))


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


def test_archive_files_handles_getmtime_exception(monkeypatch, tmp_path):
    # Prepare temp dirs
    root_dir = tmp_path / "root"
    archive_dir = tmp_path / "archive"
    root_dir.mkdir()
    archive_dir.mkdir()

    # Stub configuration and cutoff (cutoff in future so any mtime is "older")
    def fake_get_stored_ini_value(mover_name, key, ini):
        if key == "root_path":
            return str(root_dir)
        if key == "archive_path":
            return str(archive_dir)
        if key == "days_to_keep":
            return "1"
        return None

    monkeypatch.setattr(ReportFileMover, "get_stored_ini_value", fake_get_stored_ini_value)
    monkeypatch.setattr(ReportFileMover, "get_minus_days_beginning_of_day", lambda days: datetime.now() + timedelta(days=1))

    # Mock logger
    mock_logger = SimpleNamespace(debug=lambda *a, **k: None,
                                  error=pytest.monkeypatch._pytest.monkeypatch._get_test_case if False else lambda *a, **k: None,
                                  warning=lambda *a, **k: None)
    # Using a simple object with attributes to allow assertion later by wrapping methods with lists
    called = {"error": []}
    def log_error(msg):
        called["error"].append(msg)
    mock_logger.error = log_error

    def _make_scandir_cm(entries):
        class CM:
            def __enter__(self):
                return entries

            def __exit__(self, exc_type, exc, tb):
                return False

        return CM()

    monkeypatch.setattr(ReportFileMover.PurgifierLogger, "get_logger", lambda name: mock_logger)

    # Create a single file entry; scandir returns context manager
    entry = SimpleNamespace(name="file.pdf", is_file=lambda: True)
    monkeypatch.setattr(ReportFileMover.os, "scandir", lambda path: _make_scandir_cm([entry]))

    # Make os.path.getmtime raise
    def raise_getmtime(path):
        raise OSError("stat failed")
    monkeypatch.setattr(ReportFileMover.os.path, "getmtime", raise_getmtime)

    mover = ReportFileMover.ReportFileMover("MicroVUFileMover")

    # Should not raise despite getmtime raising; logger.error should have been called
    mover.archive_files()
    assert len(called["error"]) >= 1


def test_archive_files_handles_shutil_move_exception(monkeypatch, tmp_path):
    # Prepare temp dirs
    root_dir = tmp_path / "root2"
    archive_dir = tmp_path / "archive2"
    root_dir.mkdir()
    archive_dir.mkdir()

    # Stub configuration and cutoff (cutoff in future so file is considered old)
    def fake_get_stored_ini_value(mover_name, key, ini):
        if key == "root_path":
            return str(root_dir)
        if key == "archive_path":
            return str(archive_dir)
        if key == "days_to_keep":
            return "1"
        return None

    def _make_scandir_cm(entries):
        class CM:
            def __enter__(self):
                return entries

            def __exit__(self, exc_type, exc, tb):
                return False

        return CM()

    monkeypatch.setattr(ReportFileMover, "get_stored_ini_value", fake_get_stored_ini_value)
    monkeypatch.setattr(ReportFileMover, "get_minus_days_beginning_of_day", lambda days: datetime.now() + timedelta(days=1))

    # Mock logger and capture warnings
    warning_calls = []
    mock_logger = SimpleNamespace(debug=lambda *a, **k: None, error=lambda *a, **k: None, warning=lambda msg: warning_calls.append(msg))
    monkeypatch.setattr(ReportFileMover.PurgifierLogger, "get_logger", lambda name: mock_logger)

    # Create a single file entry
    entry = SimpleNamespace(name="file_to_move.pdf", is_file=lambda: True)
    monkeypatch.setattr(ReportFileMover.os, "scandir", lambda path: _make_scandir_cm([entry]))

    # Return a valid mtime (older than cutoff because cutoff is future)
    old_mtime = (datetime.today() - timedelta(days=40)).timestamp()
    monkeypatch.setattr(ReportFileMover.os.path, "getmtime", old_mtime)

    # Make shutil.move raise to simulate a move failure
    def raise_move(src, dst):
        raise shutil.Error("move failed")
    monkeypatch.setattr(ReportFileMover, "shutil", ReportFileMover.shutil)  # ensure attribute exists
    monkeypatch.setattr(ReportFileMover.shutil, "move", raise_move)

    mover = ReportFileMover.ReportFileMover("MicroVUFileMover")

    # Should not raise despite shutil.move raising; logger.warning should have been called
    mover.archive_files()
    assert any("Failed to move file" in str(w) or "move failed" in str(w) for w in warning_calls) or len(warning_calls) >= 1






