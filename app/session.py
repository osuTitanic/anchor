
from .objects.collections import Players, Channels, Matches
from .common.cache.events import EventQueue
from .clients import DefaultResponsePacket
from .common.database import Postgres
from .common.storage import Storage
from .jobs import Jobs

from twisted.python.threadpool import ThreadPool
from twisted.internet import reactor

from typing import Callable, Optional, Dict
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
bot_player = None

requests = Session()
requests.headers = {
    'User-Agent': f'bancho-{config.VERSION}'
}

handlers: Dict[DefaultResponsePacket, Callable] = {}

pool: ThreadPool = reactor.getThreadPool()
pool.adjustPoolsize(5, config.BANCHO_WORKERS)

channels = Channels()
storage = Storage()
players = Players()
matches = Matches()
jobs = Jobs()

client_manifest: Optional[dict] = None
