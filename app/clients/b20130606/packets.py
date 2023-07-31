
from .constants import RequestPacket
from typing import Callable

from ..packets import PACKETS

def register(packet: RequestPacket) -> Callable:
    def wrapper(func) -> Callable:
        PACKETS[2013606][packet] = func
        return func

    return wrapper
