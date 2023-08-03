
from .objects.collections import Players, Channels
from .common.database import Postgres
from .common.storage import Storage

from requests import Session

import logging
import config

database = Postgres(
    config.POSTGRES_USER,
    config.POSTGRES_PASSWORD,
    config.POSTGRES_HOST,
    config.POSTGRES_PORT
)

logger = logging.getLogger('bancho')

requests = Session()
requests.headers = {
    'User-Agent': f'deck-{config.VERSION}'
}

channels = Channels()
storage = Storage()
players = Players()
