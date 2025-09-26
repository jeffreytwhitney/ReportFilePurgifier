import logging


from Utilities import resolve_path, get_stored_ini_value


def get_logger(logger_name) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger_level = get_stored_ini_value("Loggers", logger_name, "PurgifierSettings")
    if logger_level == "DEBUG":
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler(resolve_path() + "\\PurgifierRunLog.txt")
    if logger_level == "DEBUG":
        file_handler.setLevel(logging.DEBUG)
    else:
        file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
