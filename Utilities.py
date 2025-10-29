"""
Utilities for path resolution, INI configuration access, simple file I/O, and date helpers.

This module provides:
- resolve_path(): Determine an application base directory depending on whether the process is frozen.
- get_ini_file_path(): Build a Windows-style path to an INI file co-located with this module.
- get_stored_ini_value(): Read a value from an INI file with a fallback to a "*" key.
- store_ini_value(): Persist a value to an INI file, creating the section if necessary.
- get_filepath_by_name(): Recursively find the first file by name starting from the current directory.
- get_file_as_string(): Read a file's contents as a string, returning an empty string on failure.
- get_minus_days_beginning_of_day(): Compute midnight of the date obtained by subtracting N days from today.
"""

import configparser
import os
import sys
from datetime import datetime, timedelta


def resolve_path():
    """
    Resolve the application's base directory.

    Returns:
        str: If running as a frozen executable (e.g., PyInstaller), returns the
        absolute directory of the current executable. Otherwise, returns the
        absolute current working directory.
    """
    return (
        os.path.abspath(os.path.dirname(sys.executable))
        if getattr(sys, "frozen", False)
        else os.path.abspath(os.path.join(os.getcwd()))
    )


def get_ini_file_path(ini_file_name):
    """
    Build the path to an INI file stored alongside this module.

    The path uses a Windows-style backslash separator and appends ".ini" to the
    provided file name.

    Args:
        ini_file_name (str): Base name of the INI file without extension.

    Returns:
        str: Full path to the INI file next to this module, e.g. "C:\\path\\to\\dir\\myapp.ini".
    """
    current_dir = resolve_path()
    return current_dir + "\\" + ini_file_name + ".ini"


def get_stored_ini_value(ini_section, ini_key, ini_filename):
    """
    Read a configuration value from an INI file.

    Attempts to read the value at [ini_section][ini_key]. If that access raises
    an IOError, it falls back to [ini_section]["*"]. If both attempts fail,
    returns an empty string.

    Args:
        ini_section (str): INI section name.
        ini_key (str): INI key within the section.
        ini_filename (str): Base INI filename (without ".ini") located next to this module.

    Returns:
        str: The configuration value, or "" if not found or on I/O error.
    """
    ini_file_path = get_ini_file_path(ini_filename)
    config = configparser.ConfigParser()
    config.read(ini_file_path)
    try:
        config_value = config.get(ini_section, ini_key)
    except IOError:
        try:
            config_value = config.get(ini_section, "*")
        except IOError:
            config_value = ""
    return config_value


def store_ini_value(ini_value, ini_section, ini_key, ini_filename):
    """
    Store a configuration value into an INI file.

    If `ini_value` is falsy (e.g., empty string), the function returns without writing.
    Ensures the target section exists, writes/updates the key, and saves the file.
    Any IOError during this process is swallowed.

    Args:
        ini_value (str): Value to store. If falsy, no write occurs.
        ini_section (str): INI section name.
        ini_key (str): INI key within the section.
        ini_filename (str): Base INI filename (without ".ini") located next to this module.

    Returns:
        None
    """
    try:
        ini_file_path = get_ini_file_path(ini_filename)
        if not ini_value:
            return

        config = configparser.ConfigParser()
        if not os.path.exists(ini_file_path):
            config.add_section(ini_section)
        else:
            if not config.has_section(ini_section):
                config.add_section(ini_section)
            config.read(ini_file_path)
        config.set(ini_section, ini_key, ini_value)
        with open(ini_file_path, "w") as conf:
            config.write(conf)
    except IOError:
        return


def get_filepath_by_name(file_name: str) -> str:
    """
    Recursively search for a file name starting at the current directory.

    Walks the directory tree rooted at "." and returns the path of the first
    file whose base name matches `file_name`.

    Args:
        file_name (str): File name to locate (e.g., "config.json").

    Returns:
        str: The first matching file path, or "" if not found.
    """
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file == file_name:
                return os.path.join(root, file)
    return ""


def get_file_as_string(file_path: str):
    """
    Read the contents of a text file as a string.

    Opens the file in text mode using the platform default encoding. If the
    file cannot be opened/read, an empty string is returned.

    Args:
        file_path (str): Path to the file.

    Returns:
        str: File contents, or "" on I/O error.
    """
    try:
        with open(file_path, "r") as f:
            return str(f.read())
    except IOError:
        return ""


def get_minus_days_beginning_of_day(days: int) -> datetime:
    """
    Compute midnight of the date obtained by subtracting `days` from today.

    Example:
        If today is 2025-09-27 and days=10, the result is 2025-09-17 00:00:00.

    Args:
        days (int): Number of days to subtract from today to determine the reference date.

    Returns:
        datetime: A naive datetime at 00:00:00 local time on (today - days).
    """
    today = datetime.today()
    date_minus_days = today - timedelta(days=days)
    beginning_of_day = date_minus_days.replace(hour=0, minute=0, second=0, microsecond=0)
    return beginning_of_day
