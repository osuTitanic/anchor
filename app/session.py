
from .objects.collections import Players, Channels
from .clients import DefaultResponsePacket
from .common.database import Postgres
from .common.storage import Storage

from typing import Callable, Dict
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

handlers: Dict[DefaultResponsePacket, Callable] = {}

channels = Channels()
storage = Storage()
players = Players()
