
from typing import Callable

from . import DefaultRequestPacket as RequestPacket

from .. import session

def register(packet: RequestPacket) -> Callable:
    def wrapper(func) -> Callable:
        session.handlers[packet] = func
        return func

    return wrapper

@register(RequestPacket.JOIN_CHANNEL)
def handle_channel_join(player, name: str):
    if not (channel := session.channels.by_name(name)):
        player.revoke_channel(name)
        return

    channel.add(player)
