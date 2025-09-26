
from Utilities import get_stored_ini_value


def test_cmm_run_data_purgifier_logger_level():
    assert get_stored_ini_value("Loggers", "cmm_run_data_purgifier_logger", "PurgifierSettings") == "INFO"


def test_micro_vu_file_mover_logger_level():
    assert get_stored_ini_value("Loggers", "micro_vu_file_mover_logger", "PurgifierSettings") == "INFO"


def test_cmm_file_mover_logger_level():
    assert get_stored_ini_value("Loggers", "cmm_file_mover_logger", "PurgifierSettings") == "INFO"


def test_cmm_run_data_purgifier_root_path():
    assert get_stored_ini_value("CMMRunDataPurgifier", "root_path", "PurgifierSettings") == r"V:\Inspect Programs\CMM Run Data"


def test_cmm_run_data_purgifier_prg_days_to_keep():
    assert get_stored_ini_value("CMMRunDataPurgifier", "cmm_prg_days_to_keep", "PurgifierSettings") == "30"


def test_cmm_run_data_purgifier_cad_days_to_keep():
    assert get_stored_ini_value("CMMRunDataPurgifier", "cmm_cad_days_to_keep", "PurgifierSettings") == "1"


def test_micro_vu_file_mover_root_path():
    assert get_stored_ini_value("MicroVUFileMover", "root_path", "PurgifierSettings") == r"S:\Micro-Vu"


def test_micro_vu_file_mover_mv_days_to_keep():
    assert get_stored_ini_value("MicroVUFileMover", "mv_days_to_keep", "PurgifierSettings") == "30"


def test_cmm_file_mover_root_path():
    assert get_stored_ini_value("CMMFileMover", "root_path", "PurgifierSettings") == r"S:\CMM"


def test_cmm_file_mover_cmm_days_to_keep():
    assert get_stored_ini_value("CMMFileMover", "cmm_days_to_keep", "PurgifierSettings") == "30"
