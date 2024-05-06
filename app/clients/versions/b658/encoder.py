
from app.common.objects import bUserStats, bUserPresence

from typing import Callable, Optional

from ..b675 import Writer
from .. import register_encoder
from . import ResponsePacket

def register(packet: ResponsePacket) -> Callable:
    def wrapper(func) -> Callable:
        register_encoder(658, packet, func)
        register_encoder(591, packet, func)
        return func

    return wrapper

@register(ResponsePacket.USER_STATS)
def send_stats(stats: bUserStats, presence: Optional[bUserPresence] = None):
    # Add cap for total score to prevent client from crashing
    stats.tscore = min(stats.tscore, 26931190826)

    writer = Writer()
    if presence:
        writer.write_presence(presence, stats)
    else:
        writer.write_stats(stats)
    return writer.stream.get()
