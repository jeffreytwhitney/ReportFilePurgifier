import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

import CMMRunDataPurgifier


def _set_mtime(path: str, dt: datetime):
    ts = dt.timestamp()
    os.utime(path, (ts, ts))


@pytest.fixture
def mock_logger(monkeypatch):
    logger = MagicMock()
    monkeypatch.setattr(CMMRunDataPurgifier.PurgifierLogger, "get_logger", lambda name: logger)
    return logger


def _make_purgifier_w_fake_imputs(root_path: str, prg_days: int, cad_days: int, monkeypatch, mock_logger):
    # Order of reads in __init__:
    # 1) ("CMMRunDataPurgifier", "root_path", "PurgifierSettings")
    # 2) ("cmm_prg_days_to_keep", "path", "PurgifierSettings")
    # 3) ("cmm_cad_days_to_keep", "path", "PurgifierSettings")
    calls = [root_path, str(prg_days), str(cad_days)]

    def fake_get(*_):
        return calls.pop(0)

    monkeypatch.setattr(CMMRunDataPurgifier, "get_stored_ini_value", fake_get)
    return CMMRunDataPurgifier.CMMRunDataPurgifier()


def test_init_logs_error_when_root_path_missing(monkeypatch, mock_logger):
    # get_stored_ini_value returns empty root path
    monkeypatch.setattr(CMMRunDataPurgifier, "get_stored_ini_value", lambda *args, **kwargs: "")

    _ = CMMRunDataPurgifier.CMMRunDataPurgifier()

    mock_logger.error.assert_any_call("Root Path not found in INI file.")


def test_init_logs_error_when_path_not_found(tmp_path, monkeypatch, mock_logger):
    calls = [str(tmp_path / "does_not_exist"), "10", "10"]

    def fake_get(*_):
        return calls.pop(0)

    monkeypatch.setattr(CMMRunDataPurgifier, "get_stored_ini_value", fake_get)
    # Make sure the first path really does not exist
    assert not os.path.exists(calls[0])

    _ = CMMRunDataPurgifier.CMMRunDataPurgifier()

    mock_logger.error.assert_any_call(f"Path not found: {str(tmp_path / 'does_not_exist')}")


def test_init_logs_error_when_prg_days_invalid(tmp_path, monkeypatch, mock_logger):
    # Root exists, prg invalid, cad valid
    calls = [str(tmp_path), "abc", "10"]

    def fake_get(*_):
        return calls.pop(0)

    monkeypatch.setattr(CMMRunDataPurgifier, "get_stored_ini_value", fake_get)

    _ = CMMRunDataPurgifier.CMMRunDataPurgifier()

    mock_logger.error.assert_any_call(
        "cmm_prg_days_to_keep returned either a non-numeric value or else not found in INI file."
    )


def test_init_logs_error_when_cad_days_invalid(tmp_path, monkeypatch, mock_logger):
    # Root exists, prg valid, cad invalid
    calls = [str(tmp_path), "10", "xyz"]

    def fake_get(*_):
        return calls.pop(0)

    monkeypatch.setattr(CMMRunDataPurgifier, "get_stored_ini_value", fake_get)

    _ = CMMRunDataPurgifier.CMMRunDataPurgifier()

    mock_logger.error.assert_any_call(
        "cmm_cad_days_to_keep returned either a non-numeric value or else not found in INI file."
    )


def test_purge_deletes_only_old_cad_files(tmp_path, monkeypatch, mock_logger):
    # Keep PRG very large so non-CAD won't be deleted by PRG rule
    prg_days = 9999
    # Delete CAD older than start-of-today
    cad_days = 0
    inst = _make_purgifier_w_fake_imputs(str(tmp_path), prg_days, cad_days, monkeypatch, mock_logger)

    old_cad = tmp_path / "old.cad"
    new_cad = tmp_path / "new.cad"
    other = tmp_path / "keep.txt"

    old_cad.write_text("x")
    new_cad.write_text("y")
    other.write_text("z")

    # Set mtimes: old_cad yesterday, new_cad now, other now
    _set_mtime(str(old_cad), datetime.now() - timedelta(days=1))
    _set_mtime(str(new_cad), datetime.now())
    _set_mtime(str(other), datetime.now())

    inst.purge_old_cmm_run_data()

    assert not old_cad.exists()
    assert new_cad.exists()
    assert other.exists()

    # Ensure we logged at least one deletion message
    assert any("Deleted:" in str(c.args[0]) for c in mock_logger.debug.call_args_list)


def test_purge_deletes_old_non_cad_by_prg_rule(tmp_path, monkeypatch, mock_logger):
    # PRG cutoff at first day of current month (0 days). Make files 40 days old to ensure deletion.
    prg_days = 0
    cad_days = 9999  # prevent CAD-specific rule from firing
    inst = _make_purgifier_w_fake_imputs(str(tmp_path), prg_days, cad_days, monkeypatch, mock_logger)

    old_txt = tmp_path / "old.txt"
    old_cad = tmp_path / "old.cad"
    new_txt = tmp_path / "new.txt"

    old_txt.write_text("a")
    old_cad.write_text("b")
    new_txt.write_text("c")

    forty_days_ago = datetime.now() - timedelta(days=40)
    _set_mtime(str(old_txt), forty_days_ago)
    _set_mtime(str(old_cad), forty_days_ago)
    _set_mtime(str(new_txt), datetime.now())

    inst.purge_old_cmm_run_data()

    assert not old_txt.exists()
    assert not old_cad.exists()
    assert new_txt.exists()


def test_purge_logs_warning_and_error_count_on_delete_failure(tmp_path, monkeypatch, mock_logger):
    prg_days = 9999
    cad_days = 0
    inst = _make_purgifier_w_fake_imputs(str(tmp_path), prg_days, cad_days, monkeypatch, mock_logger)

    bad_cad = tmp_path / "bad.cad"
    bad_cad.write_text("fail")
    _set_mtime(str(bad_cad), datetime.now() - timedelta(days=1))

    real_remove = os.remove

    def flaky_remove(path):
        if os.path.basename(path).lower() == "bad.cad":
            raise PermissionError("locked")
        return real_remove(path)

    monkeypatch.setattr(os, "remove", flaky_remove)

    inst.purge_old_cmm_run_data()

    # File should remain because deletion failed
    assert bad_cad.exists()

    # Warning about failed deletion
    assert any(
        "Failed to delete" in " ".join(map(str, c.args))
        for c in mock_logger.warning.call_args_list
    )
    # Summary warning about error count
    assert any(
        "error(s) occurred" in " ".join(map(str, c.args))
        for c in mock_logger.warning.call_args_list
    )
