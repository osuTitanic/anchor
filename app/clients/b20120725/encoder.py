

from app.common.objects import bChannel

from ..packets import PACKETS
from . import ResponsePacket
from . import Writer

from typing import Callable

def register(packet: ResponsePacket) -> Callable:
    def wrapper(func) -> Callable:
        PACKETS[20120725][1][packet] = func
        return func

    return wrapper

@register(ResponsePacket.CHANNEL_AVAILABLE)
def channel_available(channel: bChannel):
    writer = Writer()
    writer.write_channel(channel)
    return writer.stream.get()

@register(ResponsePacket.CHANNEL_AVAILABLE_AUTOJOIN)
def channel_available_autojoin(channel: bChannel):
    writer = Writer()
    writer.write_channel(channel)
    return writer.stream.get()
