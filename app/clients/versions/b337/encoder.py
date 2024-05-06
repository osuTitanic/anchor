
from typing import Callable, Optional

from app.common.objects import (
    bUserPresence,
    bUserStats,
    bUserQuit
)

from .. import register_encoder
from . import ResponsePacket
from . import Writer

def register(packet: ResponsePacket) -> Callable:
    def wrapper(func) -> Callable:
        register_encoder(337, packet, func)
        register_encoder(334, packet, func)
        return func

    return wrapper

@register(ResponsePacket.USER_STATS)
def send_stats(stats: bUserStats, presence: Optional[bUserPresence] = None):
    # Add cap for total score to prevent client from crashing
    stats.tscore = min(stats.tscore, 17705429347)

    writer = Writer()
    if presence:
        writer.write_presence(presence, stats)
    else:
        writer.write_stats(stats)
    return writer.stream.get()

@register(ResponsePacket.USER_QUIT)
def send_exit(user_quit: bUserQuit):
    writer = Writer()
    writer.write_quit(user_quit)
    return writer.stream.get()
