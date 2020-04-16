"""
    helper functions for test env
"""

import logging
import os.path

def setup_logger(test_name):
    """ set up logger for test """
    logger = logging.getLogger('logtracker')
    logger.setLevel(logging.INFO)
    logfile = '%s.log' % test_name
    reset_file(logfile)
    handler = logging.FileHandler(logfile)
    handler.setFormatter(logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    return get_logger(test_name)

def get_logger(name):
    """ return logger from test name """
    return logging.getLogger('logtracker.%s' % name)

def reset_file(file_path):
    """ empty file content """
    if os.path.exists(file_path):
        with open(file_path, "w") as _:
            pass

def create_files(lst_files):
    """ create file. if exists reset content """
    for flname in lst_files:
        with open(flname, "w") as _:
            pass

def delete_files(lst_files):
    """ delete file from disk """
    for flname in lst_files:
        if os.path.exists(flname):
            os.unlink(flname)

def write_file(file_name, words, mode="a"):
    """ write text into a file """
    with open(file_name, mode) as fdesc:
        fdesc.write(words)

def end_line(file_name, mode="a"):
    """ append line on file """
    write_file(file_name, "\n", mode)
