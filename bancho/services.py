
from .logging import ConsoleHandler
from .server import BanchoFactory

import logging

logger = logging.getLogger('anchor')
logger.setLevel(logging.DEBUG)
logger.addHandler(ConsoleHandler)

factory = BanchoFactory()
