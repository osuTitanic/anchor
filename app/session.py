
from .objects.collections import Players, Channels, Matches
from .common.helpers.filter import ChatFilter
from .common.cache.events import EventQueue
from .monitoring import RequestCounter
from .common.database import Postgres
from .common.storage import Storage
from .tasks import Tasks

from typing import Callable, Dict
from requests import Session
from chio import PacketType
from redis import Redis

import logging
import config
import time

database = Postgres(
    config.POSTGRES_USER,
    config.POSTGRES_PASSWORD,
    config.POSTGRES_HOST,
    config.POSTGRES_PORT
)

redis = Redis(
    config.REDIS_HOST,
    config.REDIS_PORT
)

events = EventQueue(
    name='bancho:events',
    connection=redis
)

logger = logging.getLogger('bancho')
startup_time = time.time()
banchobot = None

requests = Session()
requests.headers = {
    'User-Agent': f'osuTitanic/anchor ({config.DOMAIN_NAME})'
}

packets_per_minute = RequestCounter(window=60)
logins_per_minute = RequestCounter(window=60)

osu_handlers: Dict[PacketType, Callable] = {}
irc_handlers: Dict[str, Callable] = {}
filters = ChatFilter()
channels = Channels()
storage = Storage()
players = Players()
matches = Matches()
tasks = Tasks()
