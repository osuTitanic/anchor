
from .common.database import Postgres
from .logging import ConsoleHandler
from .server import BanchoFactory

import logging
import config

logger = logging.getLogger('anchor')
logger.setLevel(logging.DEBUG)
logger.addHandler(ConsoleHandler)

factory = BanchoFactory()

database = Postgres(
    config.POSTGRES_USER,
    config.POSTGRES_PASSWORD,
    config.POSTGRES_HOST,
    config.POSTGRES_PORT
)
