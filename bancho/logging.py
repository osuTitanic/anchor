
from logging import Formatter, StreamHandler
from logging import (
    CRITICAL,
    WARNING,
    ERROR,
    DEBUG,
    INFO
)

class CustomFormatter(Formatter):

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    cyan = "\x1b[96m"
    reset = "\x1b[0m"

    format_prefix = '[%(asctime)s] - <%(name)s> '
    format = '%(levelname)s: %(message)s'

    FORMATS = {
        DEBUG:    grey + format_prefix            + format + reset,
        INFO:     grey + format_prefix + cyan     + format + reset,
        WARNING:  grey + format_prefix + yellow   + format + reset,
        ERROR:    grey + format_prefix + red      + format + reset,
        CRITICAL: grey + format_prefix + bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = Formatter(log_fmt)
        return formatter.format(record)

ConsoleHandler = StreamHandler()
ConsoleHandler.setLevel(DEBUG)
ConsoleHandler.setFormatter(CustomFormatter())
