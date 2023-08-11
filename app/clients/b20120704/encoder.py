
from app.common.objects import bUserStats

from ..packets import PACKETS
from . import ResponsePacket
from . import Writer

from typing import Callable

def register(packet: ResponsePacket) -> Callable:
    def wrapper(func) -> Callable:
        PACKETS[20120704][1][packet] = func
        return func

    return wrapper

@register(ResponsePacket.USER_STATS)
def user_stats(stats: bUserStats):
    writer = Writer()
    writer.write_stats(stats)
    return writer.stream.get()
