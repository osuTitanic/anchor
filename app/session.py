
from .objects.collections import Players
from .common.database import Postgres
from .common.storage import Storage

import requests
import logging
import config

database = Postgres(
    config.POSTGRES_USER,
    config.POSTGRES_PASSWORD,
    config.POSTGRES_HOST,
    config.POSTGRES_PORT
)

logger = logging.getLogger('bancho')

session = requests.Session()
session.headers = {
    'User-Agent': f'deck-{config.VERSION}'
}

storage = Storage()
players = Players()
