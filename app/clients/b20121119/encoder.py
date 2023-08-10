
from app.common.objects import bUserPresence

from ..packets import PACKETS
from . import ResponsePacket
from .writer import Writer

from typing import Callable

def register(packet: ResponsePacket) -> Callable:
    def wrapper(func) -> Callable:
        PACKETS[20121119][1][packet] = func
        PACKETS[20121115][1][packet] = func
        return func

    return wrapper

@register(ResponsePacket.USER_PRESENCE)
def presence_asdasd(presence: bUserPresence):
    writer = Writer()
    writer.write_presence(presence)
    return writer.stream.get()
