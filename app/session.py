
from .objects.collections import Players, Channels, Matches
from .common.cache.events import EventQueue
from .clients import DefaultResponsePacket
from .common.database import Postgres
from .common.storage import Storage
from .jobs import Jobs

from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict
from requests import Session
from redis import Redis

import logging
import config

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
geolocation_cache = {}
bot_player = None

requests = Session()
requests.headers = {
    'User-Agent': f'deck-{config.VERSION}'
}

handlers: Dict[DefaultResponsePacket, Callable] = {}

# This is to prevent database overload when too many users log in at the same time
login_queue = ThreadPoolExecutor(max_workers=config.LOGIN_WORKERS)

# Used to run most of the packets in threads, except for things like messages
packet_executor = ThreadPoolExecutor(max_workers=config.PACKET_WORKERS)

# This is mostly used for database writes like messages, user activity and so on...
executor = ThreadPoolExecutor(max_workers=config.DB_WORKERS)

channels = Channels()
storage = Storage()
players = Players()
matches = Matches()
jobs = Jobs()
