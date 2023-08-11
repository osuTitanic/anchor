
from app.common.streams import StreamIn

from ..packets import PACKETS
from . import RequestPacket
from . import Reader

from typing import Callable

def register(packet: RequestPacket) -> Callable:
    def wrapper(func) -> Callable:
        PACKETS[20120812][0][packet] = func
        return func

    return wrapper

@register(RequestPacket.CHANGE_STATUS)
def change_status(stream: StreamIn):
    return Reader(stream).read_status()

@register(RequestPacket.CREATE_MATCH)
def create_match(stream: StreamIn):
    return Reader(stream).read_match()

@register(RequestPacket.MATCH_CHANGE_SETTINGS)
def change_settings(stream: StreamIn):
    return Reader(stream).read_match()

@register(RequestPacket.MATCH_CHANGE_PASSWORD)
def change_password(stream: StreamIn):
    return Reader(stream).read_match().password
