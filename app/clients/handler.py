
from ..common.constants import PresenceFilter
from ..common.objects import Message
from .. import session

from . import DefaultRequestPacket as RequestPacket

from typing import Callable, List

def register(packet: RequestPacket) -> Callable:
    def wrapper(func) -> Callable:
        session.handlers[packet] = func
        return func

    return wrapper

@register(RequestPacket.PONG)
def pong(player):
    pass

@register(RequestPacket.EXIT)
def exit(player, updating: bool):
    pass

@register(RequestPacket.RECEIVE_UPDATES)
def receive_updates(player, filter: PresenceFilter):
    player.filter = filter

@register(RequestPacket.PRESENCE_REQUEST)
def presence_request(player, players: List[int]):
    for id in players:
        if not (target := session.players.by_id(id)):
            continue

        player.enqueue_presence(target)

@register(RequestPacket.STATS_REQUEST)
def stats_request(player, players: List[int]):
    for id in players:
        if not (target := session.players.by_id(id)):
            continue

        player.enqueue_stats(target)

@register(RequestPacket.JOIN_CHANNEL)
def handle_channel_join(player, channel_name: str):
    if not (channel := session.channels.by_name(channel_name)):
        player.revoke_channel(channel_name)
        return

    channel.add(player)

@register(RequestPacket.LEAVE_CHANNEL)
def handle_channel_leave(player, channel_name: str, kick: bool = False):
    if not (channel := session.channels.by_name(channel_name)):
        player.revoke_channel(channel_name)
        return

    if kick:
        player.revoke_channel(channel_name)

    channel.remove(player)
