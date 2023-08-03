
from . import DefaultRequestPacket as RequestPacket

from ..objects.player import Player
from .. import session

from ..common.objects import (
    StatusUpdate,
    Message
)

from ..common.constants import (
    PresenceFilter,
    ClientStatus
)

from typing import Callable, List

def register(packet: RequestPacket) -> Callable:
    def wrapper(func) -> Callable:
        session.handlers[packet] = func
        return func

    return wrapper

@register(RequestPacket.PONG)
def pong(player: Player):
    pass

@register(RequestPacket.EXIT)
def exit(player: Player, updating: bool):
    player.update_activity()

@register(RequestPacket.RECEIVE_UPDATES)
def receive_updates(player: Player, filter: PresenceFilter):
    player.filter = filter

@register(RequestPacket.PRESENCE_REQUEST)
def presence_request(player: Player, players: List[int]):
    for id in players:
        if not (target := session.players.by_id(id)):
            continue

        player.enqueue_presence(target)

@register(RequestPacket.STATS_REQUEST)
def stats_request(player: Player, players: List[int]):
    for id in players:
        if not (target := session.players.by_id(id)):
            continue

        player.enqueue_stats(target)

@register(RequestPacket.CHANGE_STATUS)
def change_status(player: Player, status: StatusUpdate):
    player.status.checksum = status.beatmap_checksum
    player.status.beatmap = status.beatmap_id
    player.status.action = status.action
    player.status.mods = status.mods
    player.status.mode = status.mode
    player.status.text = status.text

    # TODO: Update rank

    player.update_activity()

    # (This needs to be done for older clients)
    session.players.send_stats(player)

@register(RequestPacket.REQUEST_STATUS)
def request_status(player: Player):
    player.enqueue_stats(player)
    # TODO: Update rank

@register(RequestPacket.JOIN_CHANNEL)
def handle_channel_join(player: Player, channel_name: str):
    if channel_name == '#spectator':
        if player.spectating:
            channel = player.spectating.spectator_chat
        else:
            channel = player.spectator_chat
    else:
        channel = session.channels.by_name(channel_name)

    # TODO: Multiplayer channels

    if not channel:
        player.revoke_channel(channel_name)
        return

    channel.add(player)

@register(RequestPacket.LEAVE_CHANNEL)
def handle_channel_leave(player: Player, channel_name: str, kick: bool = False):
    if channel_name == '#spectator':
        if player.spectating:
            channel = player.spectating.spectator_chat
        else:
            channel = player.spectator_chat
    else:
        channel = session.channels.by_name(channel_name)

    # TODO: Multiplayer channels

    if not channel:
        player.revoke_channel(channel_name)
        return

    if kick:
        player.revoke_channel(channel_name)

    channel.remove(player)

@register(RequestPacket.SEND_MESSAGE)
def send_message(player: Player, message: Message):
    if message.target == '#spectator':
        if player.spectating:
            channel = player.spectating.spectator_chat
        else:
            channel = player.spectator_chat
    else:
        channel = session.channels.by_name(message.target)

    if not channel:
        player.revoke_channel(message.target)
        return

    player.update_activity()

    # TODO: Multiplayer channels
    # TODO: Submit message to datanase
    # TODO: Commands

    channel.send_message(player, message.content)

@register(RequestPacket.SEND_PRIVATE_MESSAGE)
def send_private_message(sender: Player, message: Message):
    if not (target := session.players.by_name(message.target)):
        sender.revoke_channel(message.target)
        return

    if sender.silenced:
        return

    if target.silenced:
        # TODO: Enqueue target silenced
        return

    if target.client.friendonly_dms:
        if sender.id not in target.friends:
            sender.enqueue_blocked_dms(sender.name)
            return

    # Limit message size
    if len(message.content) > 512:
        message.content = message.content[:512] + '... (truncated)'

    sender.logger.info(f'[PM -> {target.name}]: {message.content}')
    sender.update_activity()

    # TODO: Submit to database
    # TODO: Check commands

    if target.status.action == ClientStatus.Afk and target.away_message:
        sender.enqueue_message(
            Message(
                target.name,
                target.away_message,
                target.name,
                target.id
            )
        )
        return

    target.enqueue_message(
        Message(
            sender.name,
            message.content,
            sender.name,
            sender.id
        )
    )
