

from chio import PresenceFilter, PacketType, UserStatus
from typing import Callable, List

from app.common.database import relationships
from app.clients.osu import OsuClient
from app import session

def register(packet: PacketType) -> Callable:
    def wrapper(func) -> Callable:
        session.handlers[packet] = func
        return func
    return wrapper

@register(PacketType.OsuFriendsAdd)
def add_friend(client: OsuClient, target_id: int):
    if not (target := session.players.by_id(target_id)):
        return

    if abs(target.id) in client.friends:
        return

    if target.id == client.id:
        return

    relationships.create(
        client.id,
        target_id
    )

    session.logger.info(f'{client.name} is now friends with {target.name}.')

    client.reload(client.status.mode.value)
    client.enqueue_packet(PacketType.BanchoFriendsList, client.friends)

@register(PacketType.OsuFriendsRemove)
def remove_friend(client: OsuClient, target_id: int):
    if not (target := session.players.by_id(target_id)):
        return

    if abs(target.id) not in client.friends:
        return

    relationships.delete(
        client.id,
        target_id
    )

    session.logger.info(f'{client.name} is no longer friends with {target.name}.')

    client.reload(client.status.mode.value)
    client.enqueue_packet(PacketType.BanchoFriendsList, client.friends)

@register(PacketType.OsuReceiveUpdates)
def receive_updates(client: OsuClient, filter: PresenceFilter):
    client.filter = filter

    if filter.value <= 0:
        # Client set filter to "None"
        # No players will be sent
        return

    # Account for client filter
    players = (
        session.players
        if filter == PresenceFilter.All
        else client.online_friends
    )

    client.enqueue_players(players)

@register(PacketType.OsuPresenceRequest)
def presence_request(client: OsuClient, players: List[int]):
    for id in players:
        if not (target := session.players.by_id(id)):
            continue

        client.enqueue_presence(target)

@register(PacketType.OsuPresenceRequestAll)
def presence_request_all(client: OsuClient):
    client.enqueue_players(session.players)

@register(PacketType.OsuUserStatsRequest)
def stats_request(client: OsuClient, players: List[int]):
    for id in players:
        if id is client.id:
            continue

        if not (target := session.players.by_id(id)):
            continue

        client.enqueue_stats(target)

@register(PacketType.OsuUserStatus)
def change_status(client: OsuClient, status: UserStatus):
    client.status.beatmap_checksum = status.beatmap_checksum
    client.status.beatmap_id = status.beatmap_id
    client.status.action = status.action
    client.status.mods = status.mods
    client.status.mode = status.mode
    client.status.text = status.text

    client.update_object(status.mode.value)
    client.update_status_cache()
    client.reload_rank()

    for p in client.spectators:
        # Ensure that all spectators get the latest status
        p.enqueue_stats(client)

    # Enqueue stats to clients that don't request them automatically
    session.players.send_stats(client)

@register(PacketType.OsuStatusUpdateRequest)
def request_status(client: OsuClient):
    client.reload_rank()
    client.enqueue_stats(client)
