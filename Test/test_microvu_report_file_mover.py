import os
import shutil
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

import MicroVuReportFileMover
from MicroVuReportFileMover import _get_minus_days_beginning_of_month


def _set_mtime(path: str, dt: datetime):
    ts = dt.timestamp()
    os.utime(path, (ts, ts))


@pytest.fixture
def mock_logger(monkeypatch):
    logger = MagicMock()
    monkeypatch.setattr(MicroVuReportFileMover.PurgifierLogger, "get_logger", lambda name: logger)
    return logger


def _make_instance(root_path: str, days_to_keep: int, monkeypatch):
    calls = [root_path, str(days_to_keep)]

    def fake_get(*_):
        return calls.pop(0)

    monkeypatch.setattr(MicroVuReportFileMover, "get_stored_ini_value", fake_get)
    inst = MicroVuReportFileMover.MicroVuReportFileMover()
    # Ensure cutoff is available if the code under test doesn't set it yet
    if getattr(inst, "_pdf_file_cutoff", None) is None:
        inst._pdf_file_cutoff = _get_minus_days_beginning_of_month(days_to_keep)
    return inst


def test_init_logs_error_when_root_path_missing(monkeypatch, mock_logger):
    monkeypatch.setattr(MicroVuReportFileMover, "get_stored_ini_value", lambda *args, **kwargs: "")

    _ = MicroVuReportFileMover.MicroVuReportFileMover()

    mock_logger.error.assert_any_call("Root Path not found in INI file.")


def test_init_logs_error_when_days_invalid(tmp_path, monkeypatch, mock_logger):
    calls = [str(tmp_path), "abc"]  # root, mv_days_to_keep

    def fake_get(*_):
        return calls.pop(0)

    monkeypatch.setattr(MicroVuReportFileMover, "get_stored_ini_value", fake_get)

    _ = MicroVuReportFileMover.MicroVuReportFileMover()

    mock_logger.error.assert_any_call(
        "mv_days_to_keep returned either a non-numeric value or else not found in INI file."
    )


def test_move_moves_old_files_and_creates_year_folder(tmp_path, monkeypatch, mock_logger):
    # Keep files older than start-of-today eligible by using 0 days
    inst = _make_instance(str(tmp_path), 0, monkeypatch)

    old_pdf = tmp_path / "old.pdf"
    new_pdf = tmp_path / "new.pdf"
    old_pdf.write_text("old")
    new_pdf.write_text("new")
    (tmp_path / "subdir").mkdir()  # should be skipped by is_file()

    # Set mtimes: old is yesterday, new is now
    _set_mtime(str(old_pdf), datetime.now() - timedelta(days=1))
    _set_mtime(str(new_pdf), datetime.now())

    inst.move_microvu_files()

    # Old file should be moved into year subfolder
    year_dir = tmp_path / f"_{datetime.now().strftime('%Y')}"
    moved_path = year_dir / "old.pdf"
    assert year_dir.exists()
    assert moved_path.exists()
    # New file should remain
    assert new_pdf.exists()
    # Original old should be gone
    assert not old_pdf.exists()

    # Ensure we logged directory creation and a move event
    assert any("Creating directory:" in " ".join(map(str, c.args)) for c in mock_logger.debug.call_args_list)
    assert any("Moved:" in " ".join(map(str, c.args)) for c in mock_logger.debug.call_args_list)
    # Checked count should reflect only files (2)
    assert any("Checked: 2 file(s)" in " ".join(map(str, c.args)) for c in mock_logger.debug.call_args_list)


def test_move_logs_warning_on_move_failure_and_error_summary(tmp_path, monkeypatch, mock_logger):
    inst = _make_instance(str(tmp_path), 0, monkeypatch)

    bad = tmp_path / "bad.pdf"
    bad.write_text("locked")
    _set_mtime(str(bad), datetime.now() - timedelta(days=1))

    real_move = shutil.move

    def flaky_move(src, dst, *, _bad=bad.name):
        if os.path.basename(src).lower() == _bad:
            raise PermissionError("locked")
        return real_move(src, dst)

    monkeypatch.setattr(MicroVuReportFileMover, "shutil", MicroVuReportFileMover.shutil)  # ensure we patch the module's shutil
    monkeypatch.setattr(MicroVuReportFileMover.shutil, "move", flaky_move)

    inst.move_microvu_files()

    # File should remain at original location due to failure
    assert bad.exists()
    # Warning about failed move
    assert any("Failed to move file:" in " ".join(map(str, c.args)) for c in mock_logger.warning.call_args_list)



def test_move_logs_error_on_stat_failure_and_skips_file(tmp_path, monkeypatch, mock_logger):
    inst = _make_instance(str(tmp_path), 0, monkeypatch)

    bad = tmp_path / "badstat.pdf"
    ok = tmp_path / "ok.pdf"
    bad.write_text("x")
    ok.write_text("y")
    _set_mtime(str(bad), datetime.now() - timedelta(days=1))
    _set_mtime(str(ok), datetime.now())

    real_getmtime = MicroVuReportFileMover.os.path.getmtime

    def flaky_getmtime(path):
        if os.path.basename(path).lower() == "badstat.pdf":
            raise OSError("stat failed")
        return real_getmtime(path)

    monkeypatch.setattr(MicroVuReportFileMover.os.path, "getmtime", flaky_getmtime)

    inst.move_microvu_files()

    # bad should remain (skipped after stat failure), ok should remain (not old)
    assert bad.exists()
    assert ok.exists()
    # Error log about stat failure
    assert any(
        "Failed to get file stats for file:" in " ".join(map(str, c.args)) for c in mock_logger.error.call_args_list)

