
from .common.database import Postgres
from .logging import ConsoleHandler

import logging
import config

logger = logging.getLogger('anchor')
logger.setLevel(logging.DEBUG)
logger.addHandler(ConsoleHandler)

database = Postgres(
    config.POSTGRES_USER,
    config.POSTGRES_PASSWORD,
    config.POSTGRES_HOST,
    config.POSTGRES_PORT
)
