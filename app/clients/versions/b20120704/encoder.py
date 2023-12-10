
from app.common.objects import bUserStats

from .. import register_encoder
from . import ResponsePacket
from . import Writer

from typing import Callable

def register(packet: ResponsePacket) -> Callable:
    def wrapper(func) -> Callable:
        register_encoder(20120704, packet, func)
        register_encoder(1807, packet, func)
        return func

    return wrapper

@register(ResponsePacket.USER_STATS)
def user_stats(stats: bUserStats):
    writer = Writer()
    writer.write_stats(stats)
    return writer.stream.get()
