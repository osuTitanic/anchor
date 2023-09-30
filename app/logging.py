
from app.common.database.repositories import logs

from datetime import datetime
from logging import Formatter, StreamHandler, FileHandler
from logging import (
    CRITICAL,
    WARNING,
    NOTSET,
    ERROR,
    DEBUG,
    INFO
)

import traceback
import os

class ColorFormatter(Formatter):

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
        NOTSET:   grey + format_prefix            + format + reset,
        INFO:     grey + format_prefix + cyan     + format + reset,
        WARNING:  grey + format_prefix + yellow   + format + reset,
        ERROR:    grey + format_prefix + red      + format + reset,
        CRITICAL: grey + format_prefix + bold_red + format + reset,
    }

    STRINGS = {
        DEBUG:    'debug',
        INFO:     'info',
        WARNING:  'warning',
        ERROR:    'error',
        CRITICAL: 'critical',
        NOTSET:   'notset'
    }

    DB_LEVEL = WARNING

    def format(self, record):
        try:
            if record.levelno >= self.DB_LEVEL:
                # Submit to db
                logs.create(
                    message=record.getMessage(),
                    level=self.STRINGS.get(record.levelno),
                    type=record.name
                )
        except Exception as e:
            traceback.print_exc()
            print(f'Failed to submit log to database: {e}')

        log_fmt = self.FORMATS.get(record.levelno)
        formatter = Formatter(log_fmt)
        return formatter.format(record)

os.makedirs('logs', exist_ok=True)

Console = StreamHandler()
Console.setFormatter(ColorFormatter())

File = FileHandler(f'logs/{datetime.now().strftime("%Y-%m-%d")}.log', mode='a', encoding='utf-8')
File.setFormatter(
    Formatter(
        '[%(asctime)s] - <%(name)s> %(levelname)s: %(message)s'
    )
)
