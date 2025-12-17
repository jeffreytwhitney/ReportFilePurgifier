from CMMRunDataPurgifier import CMMRunDataPurgifier
from ReportFileMover import ReportFileMover
from Utilities import get_stored_ini_value, trim_log_file


def purge_old_cmm_run_data():
    """
    Scan the root directory and purge files based on cutoff policies.
    """
    purgifier = CMMRunDataPurgifier()
    purgifier.purge_old_cmm_run_data()


def move_old_report_files(file_mover_name):
    """
    Moves old report files by instantiating a ReportFileMover object and invoking its
    archiving functionality. This function is designed to facilitate the organization
    and archiving of report files through a predefined process encapsulated within
    the ReportFileMover class.

    :param file_mover_name: Name of the file mover instance to be used for
        identifying and processing the report files.
    :type file_mover_name: str
    :return: None
    """
    file_mover = ReportFileMover(file_mover_name)
    file_mover.archive_files()


if __name__ == "__main__":
    purge_old_cmm_run_data()

    file_movers = get_stored_ini_value("ReportFileMovers", "file_movers", "PurgifierSettings").split(",")
    for mover in file_movers:
        move_old_report_files(mover.strip())

    trim_log_file("PurgifierRunLog")
