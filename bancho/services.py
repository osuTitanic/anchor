
from .common.database import Postgres
from .common.users import UserCache
from .jobs import Jobs

import logging
import config

logger = logging.getLogger('anchor')

database = Postgres(
    config.POSTGRES_USER,
    config.POSTGRES_PASSWORD,
    config.POSTGRES_HOST,
    config.POSTGRES_PORT
)

cache = UserCache()

bot_player = None

from .objects.collections import Players, Channels, Matches

jobs = Jobs(max_workers=4)
players = Players()
matches = Matches()
channels = Channels()
ip_cache = set()
