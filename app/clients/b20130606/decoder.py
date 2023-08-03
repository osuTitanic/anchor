
from app.common.constants import PresenceFilter
from app.common.streams import StreamIn

from .constants import RequestPacket
from ..packets import PACKETS
from .reader import Reader

from typing import Callable

import app

def register(packet: RequestPacket) -> Callable:
    def wrapper(func) -> Callable:
        PACKETS[2013606][0][packet] = func
        return func

    return wrapper

@register(RequestPacket.PONG)
def pong(stream: StreamIn):
    return

@register(RequestPacket.EXIT)
def exit(stream: StreamIn):
    return stream.s32() == 1

@register(RequestPacket.RECEIVE_UPDATES)
def receive_updates(stream: StreamIn):
    return PresenceFilter(stream.s32())

@register(RequestPacket.PRESENCE_REQUEST)
def presence_request(stream: StreamIn):
    return Reader(stream).read_intlist()

@register(RequestPacket.STATS_REQUEST)
def stats_request(stream: StreamIn):
    return Reader(stream).read_intlist()

@register(RequestPacket.REQUEST_STATUS)
def request_status(stream: StreamIn):
    return

@register(RequestPacket.CHANGE_STATUS)
def change_status(stream: StreamIn):
    return Reader(stream).read_status()

@register(RequestPacket.JOIN_CHANNEL)
def join_channel(stream: StreamIn):
    return stream.string()

@register(RequestPacket.LEAVE_CHANNEL)
def leave_channel(stream: StreamIn):
    return stream.string()

@register(RequestPacket.SEND_MESSAGE)
def send_message(stream: StreamIn):
    return Reader(stream).read_message()

@register(RequestPacket.SEND_PRIVATE_MESSAGE)
def send_message_private(stream: StreamIn):
    return Reader(stream).read_message()

@register(RequestPacket.ADD_FRIEND)
def add_friend(stream: StreamIn):
    return stream.s32()

@register(RequestPacket.REMOVE_FRIEND)
def remove_friend(stream: StreamIn):
    return stream.s32()
