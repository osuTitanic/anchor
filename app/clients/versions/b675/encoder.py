
from app.common.objects import bUserStats, bUserPresence

from typing import Callable, Optional

from .. import register_encoder
from . import ResponsePacket
from . import Writer

def register(packet: ResponsePacket) -> Callable:
    def wrapper(func) -> Callable:
        register_encoder(675, packet, func)
        register_encoder(657, packet, func)
        return func

    return wrapper

@register(ResponsePacket.USER_STATS)
def send_stats(stats: bUserStats, presence: Optional[bUserPresence] = None):
    writer = Writer()
    if presence:
        writer.write_presence(presence, stats)
    else:
        writer.write_stats(stats)
    return writer.stream.get()
