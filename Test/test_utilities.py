import os
import sys
import configparser
import builtins
import Utilities
from pathlib import Path
import pytest
from datetime import datetime, timedelta


def test_resolve_path_frozen(monkeypatch, tmp_path):
    exe_dir = tmp_path / "bin"
    exe_dir.mkdir()
    exe_path = exe_dir / "app.exe"
    exe_path.write_text("")  # file existence not required, but harmless

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_path), raising=False)

    result = Utilities.resolve_path()
    assert os.path.normcase(os.path.abspath(result)) == os.path.normcase(os.path.abspath(str(exe_dir)))


def test_resolve_path_non_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.chdir(tmp_path)

    result = Utilities.resolve_path()
    assert os.path.normcase(result) == os.path.normcase(os.path.abspath(str(tmp_path)))


def test_get_ini_file_path_uses_module_dir(monkeypatch, tmp_path):
    # Simulate the module being located in tmp_path
    monkeypatch.setattr(Utilities, "__file__", str(tmp_path / "Utilities.py"), raising=False)
    expected = f"{str(tmp_path)}\\myapp.ini"
    assert Utilities.get_ini_file_path("myapp") == expected


def test_get_stored_ini_value_success(monkeypatch, tmp_path):
    # Arrange a real INI file at the computed path
    monkeypatch.setattr(Utilities, "__file__", str(tmp_path / "Utilities.py"), raising=False)
    ini_path = Utilities.get_ini_file_path("app")
    cfg = configparser.ConfigParser()
    cfg.add_section("section")
    cfg.set("section", "key", "value123")
    with open(ini_path, "w") as f:
        cfg.write(f)

    # Act
    result = Utilities.get_stored_ini_value("section", "key", "app")

    # Assert
    assert result == "value123"


def test_get_stored_ini_value_falls_back_to_star_via_ioerror(monkeypatch):
    # Mock ConfigParser to raise IOError for the specific key, then succeed for "*"
    class FakeConfig:
        def __init__(self):
            self.calls = 0

        def read(self, path):
            pass

        def get(self, section, key):
            self.calls += 1
            if self.calls == 1:
                raise IOError("simulated failure on concrete key")
            if key == "*":
                return "star-value"
            raise IOError("unexpected")

        def has_section(self, section):
            return True

    monkeypatch.setattr(Utilities.configparser, "ConfigParser", lambda: FakeConfig())
    result = Utilities.get_stored_ini_value("any", "missing-key", "irrelevant")
    assert result == "star-value"


def test_get_stored_ini_value_returns_empty_when_both_fail(monkeypatch):
    class AlwaysFailConfig:
        def read(self, path):
            pass

        def get(self, section, key):
            raise IOError("always fail")

        def has_section(self, section):
            return False

    monkeypatch.setattr(Utilities.configparser, "ConfigParser", lambda: AlwaysFailConfig())
    result = Utilities.get_stored_ini_value("any", "any", "irrelevant")
    assert result == ""


def test_store_ini_value_no_write_when_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(Utilities, "__file__", str(tmp_path / "Utilities.py"), raising=False)
    ini_path = Utilities.get_ini_file_path("app")
    Utilities.store_ini_value("", "sec", "key", "app")
    assert not os.path.exists(ini_path)


def test_store_ini_value_write_and_update(monkeypatch, tmp_path):
    monkeypatch.setattr(Utilities, "__file__", str(tmp_path / "Utilities.py"), raising=False)
    ini_path = Utilities.get_ini_file_path("app")

    # First write
    Utilities.store_ini_value("v1", "sec", "key", "app")
    cfg = configparser.ConfigParser()
    cfg.read(ini_path)
    assert cfg.get("sec", "key") == "v1"

    # Update existing
    Utilities.store_ini_value("v2", "sec", "key", "app")
    cfg2 = configparser.ConfigParser()
    cfg2.read(ini_path)
    assert cfg2.get("sec", "key") == "v2"


def test_get_filepath_by_name_found(monkeypatch, tmp_path):
    # Arrange a nested file structure
    monkeypatch.chdir(tmp_path)
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    target = nested / "target.txt"
    target.write_text("hello")

    found = Utilities.get_filepath_by_name("target.txt")
    assert found, "Expected a non-empty path"
    assert os.path.basename(found) == "target.txt"
    assert os.path.exists(found)


def test_get_filepath_by_name_not_found(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert Utilities.get_filepath_by_name("does_not_exist.xyz") == ""


def test_get_file_as_string_reads_content(tmp_path):
    p = tmp_path / "file.txt"
    p.write_text("abc123")
    assert Utilities.get_file_as_string(str(p)) == "abc123"


def test_get_file_as_string_missing_returns_empty(tmp_path):
    p = tmp_path / "missing.txt"
    assert Utilities.get_file_as_string(str(p)) == ""


def test_get_minus_days_beginning_of_day(monkeypatch):
    # Freeze "today" to a known datetime; expect midnight of (today - days)
    class FixedDateTime(datetime):
        @classmethod
        def today(cls):
            return cls(2025, 9, 27, 13, 45, 8, 999999)

    monkeypatch.setattr(Utilities, "datetime", FixedDateTime, raising=True)
    result = Utilities.get_minus_days_beginning_of_day(10)
    assert isinstance(result, datetime)
    assert result == datetime(2025, 9, 17, 0, 0, 0, 0)