import configparser
import os
import sys


def resolve_path():
    return (
        os.path.abspath(os.path.dirname(sys.executable))
        if getattr(sys, "frozen", False)
        else os.path.abspath(os.path.join(os.getcwd()))
    )


def get_ini_file_path(ini_file_name):
    current_dir = os.path.dirname(__file__)
    return current_dir + "\\" + ini_file_name + ".ini"


def get_stored_ini_value(ini_section, ini_key, ini_filename):
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
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file == file_name:
                return os.path.join(root, file)
    return ""


def get_file_as_string(file_path: str):
    try:
        with open(file_path, "r") as f:
            return str(f.read())
    except IOError:
        return ""
