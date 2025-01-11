import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logger = logging.getLogger("speechgpt_logger")
logger.setLevel(logging.DEBUG)

log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)


def get_logger():
    return logger
