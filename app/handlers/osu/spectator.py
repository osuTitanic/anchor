
from chio import PacketType, ReplayFrameBundle
from typing import Callable

from app.clients.osu import OsuClient
from app import session

def register(packet: PacketType) -> Callable:
    def wrapper(func) -> Callable:
        session.osu_handlers[packet] = func
        return func
    return wrapper

@register(PacketType.OsuStartSpectating)
def start_spectating(client: OsuClient, player_id: int):
    if player_id == client.id:
        client.logger.warning('Failed to start spectating: Player tried to spectate himself?')
        return

    if player_id == -1:
        # This can happen on tourney clients
        return

    if not (target := session.players.by_id(player_id)):
        client.logger.warning(f'Failed to start spectating: Player with id "{player_id}" was not found!')
        return

    if target.id == session.banchobot.id:
        client.logger.warning(f'Tried to spectate {session.banchobot.name}.')
        return

    if (client.spectating or client in target.spectators) and not client.is_tourney_client:
        stop_spectating(client)

    client.logger.info(f'Started spectating "{target.name}".')
    client.spectating = target

    # Enqueue to target
    target.spectators.add(client)
    target.enqueue_packet(PacketType.BanchoSpectatorJoined, client.id)

    # Enqueue fellow spectators
    for p in target.spectators:
        client.enqueue_packet(PacketType.BanchoFellowSpectatorJoined, p.id)
        p.enqueue_packet(PacketType.BanchoFellowSpectatorJoined, client.id)

    # Join their channel
    client.enqueue_channel(target.spectator_chat.bancho_channel, autojoin=True)
    target.spectator_chat.add(client)

    # Check if target joined #spectator
    if target not in target.spectator_chat.users:
        target.enqueue_channel(target.spectator_chat.bancho_channel)
        target.spectator_chat.add(target)

@register(PacketType.OsuStopSpectating)
def stop_spectating(client: OsuClient):
    if not client.spectating:
        client.logger.warning('Failed to stop spectating: Player is not spectating!')
        return

    # Remove from target spectators
    client.spectating.spectators.discard(client)

    # Leave spectator channel
    client.spectating.spectator_chat.remove(client)
    client.enqueue_channel_revoked("#spectator")

    # Enqueue to target
    client.spectating.enqueue_packet(PacketType.BanchoSpectatorLeft, client.id)

    # Enqueue to others
    for p in client.spectating.spectators:
        p.enqueue_packet(PacketType.BanchoFellowSpectatorLeft, client.id)

    client.logger.info(f'Stopped spectating "{client.spectating.name}".')
    client.spectating = None

@register(PacketType.OsuCantSpectate)
def cant_spectate(client: OsuClient):
    if not client.spectating:
        return

    client.logger.info(f"Player is missing beatmap to spectate.")
    client.spectating.enqueue_packet(PacketType.BanchoSpectatorCantSpectate, client.id)

    for p in client.spectating.spectators:
        p.enqueue_packet(PacketType.BanchoSpectatorCantSpectate, client.id)

@register(PacketType.OsuSpectateFrames)
def send_frames(client: OsuClient, bundle: ReplayFrameBundle):
    if not client.spectators:
        return

    if len(client.spectators) <= 256:
        return broadcast_frames(client, bundle)

    # Send them to the queue, if there
    # are too many spectators
    session.tasks.do_later(
        broadcast_frames,
        client, bundle,
        priority=1
    )

def broadcast_frames(client: OsuClient, bundle: ReplayFrameBundle):
    for p in client.spectators:
        p.enqueue_packet(PacketType.BanchoSpectateFrames, bundle)
