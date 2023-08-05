
from . import DefaultResponsePacket as ResponsePacket
from . import DefaultRequestPacket as RequestPacket

from ..common.database.objects import DBBeatmap
from ..objects.multiplayer import Match
from ..objects.channel import Channel
from ..objects.player import Player
from .. import session

from ..common.database.repositories import (
    relationships,
    beatmaps,
    messages,
    scores
)

from ..common.objects import (
    bBeatmapInfoRequest,
    bReplayFrameBundle,
    bBeatmapInfoReply,
    bStatusUpdate,
    bBeatmapInfo,
    bMatchJoin,
    bMessage,
    bMatch
)

from ..common.constants import (
    MatchTeamTypes,
    PresenceFilter,
    ClientStatus,
    SlotStatus,
    SlotTeam,
    Grade
)

from typing import Callable, Tuple, List

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

@register(RequestPacket.PRESENCE_REQUEST_ALL)
def presence_request_all(player: Player):
    player.enqueue_players(session.players)

@register(RequestPacket.STATS_REQUEST)
def stats_request(player: Player, players: List[int]):
    for id in players:
        if not (target := session.players.by_id(id)):
            continue

        player.enqueue_stats(target)

@register(RequestPacket.CHANGE_STATUS)
def change_status(player: Player, status: bStatusUpdate):
    player.status.checksum = status.beatmap_checksum
    player.status.beatmap = status.beatmap_id
    player.status.action = status.action
    player.status.mods = status.mods
    player.status.mode = status.mode
    player.status.text = status.text

    player.update_activity()
    player.reload_rank()

    # (This needs to be done for older clients)
    session.players.send_stats(player)

@register(RequestPacket.REQUEST_STATUS)
def request_status(player: Player):
    player.enqueue_stats(player)
    player.reload_rank()

@register(RequestPacket.JOIN_CHANNEL)
def handle_channel_join(player: Player, channel_name: str):
    if channel_name == '#spectator':
        if player.spectating:
            channel = player.spectating.spectator_chat
        else:
            channel = player.spectator_chat
    elif channel_name == '#multiplayer':
        channel = player.match.chat
    else:
        channel = session.channels.by_name(channel_name)

    if not channel:
        player.revoke_channel(channel_name)
        return

    channel.add(player)

@register(RequestPacket.LEAVE_CHANNEL)
def channel_leave(player: Player, channel_name: str, kick: bool = False):
    if channel_name == '#spectator':
        if player.spectating:
            channel = player.spectating.spectator_chat
        else:
            channel = player.spectator_chat
    elif channel_name == '#multiplayer':
        channel = player.match.chat
    else:
        channel = session.channels.by_name(channel_name)

    if not channel:
        player.revoke_channel(channel_name)
        return

    if kick:
        player.revoke_channel(channel_name)

    channel.remove(player)

@register(RequestPacket.SEND_MESSAGE)
def send_message(player: Player, message: bMessage):
    if message.target == '#spectator':
        if player.spectating:
            channel = player.spectating.spectator_chat
        else:
            channel = player.spectator_chat
    elif message.target == '#multiplayer':
        channel = player.match.chat
    else:
        channel = session.channels.by_name(message.target)

    if not channel:
        player.revoke_channel(message.target)
        return

    player.update_activity()
    channel.send_message(player, message.content)

    # TODO: Commands

    messages.create(
        player.name,
        channel.name,
        message.content
    )

@register(RequestPacket.SEND_PRIVATE_MESSAGE)
def send_private_message(sender: Player, message: bMessage):
    if not (target := session.players.by_name(message.target)):
        sender.revoke_channel(message.target)
        return

    if sender.silenced:
        return

    if target.silenced:
        sender.enqueue_silenced_target(target.name)
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

    # TODO: Check commands

    messages.create(
        sender.name,
        target.name,
        message.content
    )

    if target.away_message:
        sender.enqueue_message(
            bMessage(
                target.name,
                 f'\x01ACTION is away: {target.away_message}\x01',
                target.name,
                target.id
            )
        )

    target.enqueue_message(
        bMessage(
            sender.name,
            message.content,
            sender.name,
            sender.id
        )
    )

@register(RequestPacket.SET_AWAY_MESSAGE)
def away_message(player: Player, message: bMessage):
    if player.away_message is None and message.content == "":
        return

    if message.content != "":
        player.away_message = message.content
        player.enqueue_message(
            bMessage(
                session.bot_player.name,
                f'You have been marked as away: {message.content}',
                session.bot_player.name,
                session.bot_player.id
            )
        )
    else:
        player.away_message = None
        player.enqueue_message(
            bMessage(
                session.bot_player.name,
                'You are no longer marked as being away',
                session.bot_player.name,
                session.bot_player.id
            )
        )

@register(RequestPacket.ADD_FRIEND)
def add_friend(player: Player, target_id: int):
    if not (target := session.players.by_id(target_id)):
        return

    if target.id in player.friends:
        return

    relationships.create(
        player.id,
        target.id
    )

    session.logger.info(f'{player.name} is now friends with {target.name}.')

    player.reload_object()
    player.enqueue_friends()

@register(RequestPacket.REMOVE_FRIEND)
def remove_friend(player: Player, target_id: int):
    if not (target := session.players.by_id(target_id)):
        return

    if target.id not in player.friends:
        return

    relationships.delete(
        player.id,
        target.id
    )

    session.logger.info(f'{player.name} no longer friends with {target.name}.')

    player.reload_object()
    player.enqueue_friends()

@register(RequestPacket.BEATMAP_INFO)
def beatmap_info(player: Player, info: bBeatmapInfoRequest):
    maps: List[Tuple[int, DBBeatmap]] = []

    # Fetch all matching beatmaps from database

    for index, filename in enumerate(info.filenames):
        if not (beatmap := beatmaps.fetch_by_file(filename)):
            continue

        maps.append((
            index,
            beatmap
        ))

    for id in info.beatmap_ids:
        if not (beatmap := beatmaps.fetch_by_id(id)):
            continue

        maps.append((
            -1,
            beatmap
        ))

    # Create beatmap response

    map_infos: List[bBeatmapInfo] = []

    for index, beatmap in maps:
        ranked = {
            -2: 0, # Graveyard: Pending
            -1: 0, # WIP: Pending
             0: 0, # Pending: Pending
             1: 1, # Ranked: Ranked
             2: 2, # Approved: Approved
             3: 2, # Qualified: Approved
             4: 2, # Loved: Approved
        }[beatmap.status]

        # Get personal best in every mode for this beatmap
        grades = {
            0: Grade.N,
            1: Grade.N,
            2: Grade.N,
            3: Grade.N
        }

        for mode in range(4):
            personal_best = scores.fetch_personal_best(
                beatmap.id,
                player.id,
                mode
            )

            if personal_best:
                grades[mode] = Grade[personal_best.grade]

        map_infos.append(
            bBeatmapInfo(
                index,
                beatmap.id,
                beatmap.set_id,
                beatmap.set_id, # thread_id
                ranked,
                grades[0], # standard
                grades[2], # fruits
                grades[1], # taiko
                grades[3], # mania
                beatmap.md5
            )
        )

    player.send_packet(
        ResponsePacket.BEATMAP_INFO_REPLY,
        bBeatmapInfoReply(map_infos)
    )

@register(RequestPacket.START_SPECTATING)
def start_spectating(player: Player, player_id: int):
    if not (target := session.players.by_id(player_id)):
        return

    if target.id == session.bot_player.id:
        return

    # TODO: Check osu! mania support

    if (player.spectating) or (player in target.spectators):
        stop_spectating(player)
        return

    player.spectating = target

    # Join their channel
    player.enqueue_channel(target.spectator_chat)
    target.spectator_chat.add(player)

    # Enqueue to others
    for p in target.spectators:
        p.enqueue_fellow_spectator(player.id)

    # Enqueue to target
    target.spectators.append(player)
    target.enqueue_spectator(player.id)
    target.enqueue_channel(target.spectator_chat)

    # Check if target joined #spectator
    if target not in target.spectator_chat.users:
        target.spectator_chat.add(target)

@register(RequestPacket.STOP_SPECTATING)
def stop_spectating(player: Player):
    if not player.spectating:
        return

    # Leave spectator channel
    player.spectating.spectator_chat.remove(player)

    # Remove from target
    player.spectating.spectators.remove(player)

    # Enqueue to others
    for p in player.spectating.spectators:
        p.enqueue_fellow_spectator_left(player.id)

    # Enqueue to target
    player.spectating.enqueue_spectator_left(player.id)

    # If target has no spectators anymore
    # kick them from the spectator channel
    if not player.spectating.spectators:
        player.spectating.spectator_chat.remove(
            player.spectating
        )

    player.spectating = None

@register(RequestPacket.CANT_SPECTATE)
def cant_spectate(player: Player):
    if not player.spectating:
        return

    player.spectating.enqueue_cant_spectate(player.id)

    for p in player.spectating.spectators:
        p.enqueue_cant_spectate(player.id)

@register(RequestPacket.SEND_FRAMES)
def send_frames(player: Player, bundle: bReplayFrameBundle):
    if not player.spectators:
        return

    # TODO: Check osu! mania support

    for p in player.spectators:
        p.enqueue_frames(bundle)

@register(RequestPacket.JOIN_LOBBY)
def join_lobby(player: Player):
    for p in session.players:
        p.enqueue_lobby_join(player.id)

    # TODO: Enqueue matches

    player.in_lobby = True

@register(RequestPacket.PART_LOBBY)
def part_lobby(player: Player):
    player.in_lobby = False

    for p in session.players:
        p.enqueue_lobby_part(player.id)

@register(RequestPacket.MATCH_INVITE)
def invite(player: Player, target_id: int):
    if player.silenced:
        return

    if not (target := session.players.by_id(target_id)):
        return

    # TODO: Check invite spams

    # TODO:
    # target.enqueue_invite(
    #     Message(
    #         player.name,
    #         'Come join my multiplayer match: [osump://...]',
    #         player.name,
    #         player.id
    #     )
    # )

@register(RequestPacket.CREATE_MATCH)
def create_match(player: Player, bancho_match: bMatch):
    if not player.in_lobby:
        player.enqueue_matchjoin_fail()
        return

    if player.silenced:
        player.enqueue_matchjoin_fail()
        return

    match = Match.from_bancho_match(bancho_match)

    if not session.matches.append(match):
        player.enqueue_matchjoin_fail()
        return

    session.channels.append(
        c := Channel(
            name=f'#multi_{match.id}',
            topic=match.name,
            owner=match.host.name,
            read_perms=1,
            write_perms=1,
            public=False
        )
    )
    match.chat = c

    session.logger.info(f'Created match: "{match.name}"')

    join_match(
        player,
        bMatchJoin(
            match.id,
            match.password
        )
    )

@register(RequestPacket.JOIN_MATCH)
def join_match(player: Player, match_join: bMatchJoin):
    if not (match := session.matches[match_join.match_id]):
        # Match was not found
        player.enqueue_matchjoin_fail()
        player.enqueue_match_disband(match_join.match_id)
        return

    if player.match:
        # Player already joined the match
        player.enqueue_matchjoin_fail()
        return

    if player is not match.host:
        # TODO: Check password
        slot_id = 124
    else:
        # Player is creating the match
        slot_id = 0

    # Join the chat
    match.chat.add(player)

    # Leave the lobby channel
    channel_leave(
        player,
        '#lobby',
        kick=True
    )

    slot = match.slots[0 if slot_id == -1 else slot_id]

    if match.team_type in (MatchTeamTypes.TeamVs, MatchTeamTypes.TagTeamVs):
        slot.team = SlotTeam.Red

    slot.status = SlotStatus.NotReady
    slot.player = player

    player.match = match

    player.enqueue_matchjoin_success(match.bancho_match)
    # TODO: match.update()

@register(RequestPacket.CHANGE_FRIENDONLY_DMS)
def change_friendonly_dms(player: Player, enabled: bool):
    player.client.friendonly_dms = enabled
