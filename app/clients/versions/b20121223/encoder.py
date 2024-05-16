
from app.common.objects import bMessage

from .. import register_encoder
from . import ResponsePacket
from . import Writer

from typing import Callable

def register(packet: ResponsePacket) -> Callable:
    def wrapper(func) -> Callable:
        register_encoder(20121223, packet, func)
        register_encoder(20121203, packet, func)
        return func

    return wrapper

@register(ResponsePacket.SEND_MESSAGE)
def message(message: bMessage):
    writer = Writer()
    writer.write_message(message)
    return writer.stream.get()

@register(ResponsePacket.TARGET_IS_SILENCED)
def target_silenced(msg: bMessage):
    writer = Writer()
    writer.write_message(msg)
    return writer.stream.get()

@register(ResponsePacket.USER_DM_BLOCKED)
def dm_blocked(msg: bMessage):
    writer = Writer()
    writer.write_message(msg)
    return writer.stream.get()

@register(ResponsePacket.INVITE)
def match_invite(msg: bMessage):
    writer = Writer()
    writer.write_message(msg)
    return writer.stream.get()