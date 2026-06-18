
from .objects.collections import Players, Channels, Matches
from .common.helpers.filter import ChatFilter
from .common.cache.events import EventQueue
from .monitoring import RequestCounter
from .common.database import Postgres
from .common.storage import Storage
from .common.config import Config
from .tasks import Tasks

from typing import Callable, Dict, TYPE_CHECKING
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from requests import Session
from chio import PacketType
from redis import Redis

if TYPE_CHECKING:
    from .banchobot import BanchoBot

import logging
import time

config = Config()
database = Postgres(config)
storage = Storage(config)

redis = Redis(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    password=config.REDIS_PASS,
    decode_responses=False
)
events = EventQueue(
    name='bancho:events',
    connection=redis
)

logger = logging.getLogger('bancho')
startup_time = time.time()
banchobot: "BanchoBot"

requests = Session()
requests.headers.update({
    'User-Agent': f'osuTitanic/anchor ({config.DOMAIN_NAME})'
})

retries = Retry(
    total=4,
    backoff_factor=0.3,
    status_forcelist=[500, 502, 503, 504]
)
requests.mount('http://', HTTPAdapter(max_retries=retries))
requests.mount('https://', HTTPAdapter(max_retries=retries))

packets_per_minute = RequestCounter(window=60)
logins_per_minute = RequestCounter(window=60)

osu_handlers: Dict[PacketType, Callable] = {}
irc_handlers: Dict[str, Callable] = {}
blocked_connections = set()
filters = ChatFilter()
channels = Channels()
players = Players()
matches = Matches()
tasks = Tasks()
