
from .objects.collections import Players
from .common.database import Postgres
from .common.storage import Storage

import logging
import config

database = Postgres(
    config.POSTGRES_USER,
    config.POSTGRES_PASSWORD,
    config.POSTGRES_HOST,
    config.POSTGRES_PORT
)

logger = logging.getLogger('bancho')

storage = Storage()
players = Players()
