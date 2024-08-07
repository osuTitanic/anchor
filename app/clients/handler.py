
from . import DefaultResponsePacket as ResponsePacket
from . import DefaultRequestPacket as RequestPacket

from ..common.database.objects import DBBeatmap, DBScore
from ..common.database.repositories import wrapper
from ..objects.multiplayer import Match
from ..objects.channel import Channel
from ..objects.player import Player
from ..common import officer
from .. import session, commands

from ..common.database.repositories import (
    relationships,
    beatmaps,
    messages,
    matches,
    events
)

from ..common.objects import (
    bBeatmapInfoRequest,
    bReplayFrameBundle,
    bBeatmapInfoReply,
    bStatusUpdate,
    bBeatmapInfo,
    bScoreFrame,
    bMatchJoin,
    bMessage,
    bMatch
)

from ..common.constants import (
    MatchScoringTypes,
    MatchTeamTypes,
    PresenceFilter,
    SlotStatus,
    EventType,
    SlotTeam,
    GameMode,
    Grade,
    Mods
)

from typing import Callable, Tuple, Optional, List
from sqlalchemy.orm import selectinload
from twisted.internet import reactor
from datetime import datetime
from copy import copy

import config
import time

def register(packet: RequestPacket) -> Callable:
    def wrapper(func) -> Callable:
        session.handlers[packet] = func
        return func

    return wrapper

@wrapper.exception_wrapper()
def resolve_channel(channel_name: str, player: Player) -> Optional[Channel]:
    if channel_name == '#spectator':
        # Select spectator chat
        return (
            player.spectating.spectator_chat
            if player.spectating else
               player.spectator_chat
        )

    elif channel_name == '#multiplayer':
        # Select multiplayer chat
        return player.match.chat

    # Resolve channel by name
    if channel := session.channels.by_name(channel_name):
        return channel

@register(RequestPacket.PONG)
def pong(player: Player):
    pass # lol

@register(RequestPacket.EXIT)
def exit(player: Player, updating: bool):
    player.update_activity()
    player.close_connection()

@register(RequestPacket.RECEIVE_UPDATES)
def receive_updates(player: Player, filter: PresenceFilter):
    player.filter = filter

    if filter.value <= 0:
        # Client set filter to "None"
        # No players will be sent
        return

    # Account for player filter
    players = (
        session.players
        if filter == PresenceFilter.All
        else player.online_friends
    )

    player.enqueue_players(players, stats_only=True)

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

    player.update_status_cache()
    player.update_activity()
    player.reload_rank()

    # (This needs to be done for older clients)
    session.players.send_stats(player)

@register(RequestPacket.REQUEST_STATUS)
def request_status(player: Player):
    player.reload_rank()
    player.enqueue_stats(player)

@register(RequestPacket.JOIN_CHANNEL)
def handle_channel_join(player: Player, channel_name: str):
    client_channels = [
        '#userlog',
        '#highlight'
    ]

    if channel_name in client_channels:
        player.join_success(channel_name)
        return

    if not (channel := resolve_channel(channel_name, player)):
        player.revoke_channel(channel_name)
        return

    channel.add(player)

@register(RequestPacket.LEAVE_CHANNEL)
def channel_leave(player: Player, channel_name: str, kick: bool = False):
    if not (channel := resolve_channel(channel_name, player)):
        player.revoke_channel(channel_name)
        return

    if kick:
        player.revoke_channel(channel_name)

    channel.remove(player)

@register(RequestPacket.SEND_MESSAGE)
def send_message(player: Player, message: bMessage):
    client_channels = [
        '#userlog',
        '#highlight'
    ]

    if message.target in client_channels:
        return

    if not (channel := resolve_channel(message.target, player)):
        player.revoke_channel(message.target)
        return

    if message.content.startswith('/me'):
        message.content = f'\x01ACTION{message.content.removeprefix("/me")}\x01'

    if (time.time() - player.last_minute_stamp) > 10:
        player.last_minute_stamp = time.time()
        player.recent_message_count = 0

    if player.recent_message_count > 35 and not player.is_bot:
        player.silence(60, reason='Chat spamming')
        return

    if (parsed_message := message.content.strip()).startswith('!'):
        # A command was executed
        commands.execute(player, channel, parsed_message)
        return

    channel.send_message(
        player,
        parsed_message,
        submit_to_database=True
    )

    player.update_activity()
    player.recent_message_count += 1

@register(RequestPacket.SEND_PRIVATE_MESSAGE)
def send_private_message(sender: Player, message: bMessage):
    if message.target == 'peppy':
        # This could be an internal osu! anti-cheat message
        officer.call(f'{sender.name} tried to message peppy: "{message.content}"')
        return

    if not (target := session.players.by_name(message.target)):
        sender.revoke_channel(message.target)
        return

    if target.id == sender.id:
        # This is somehow possible in b1700
        return

    if sender.silenced:
        sender.logger.warning(
            'Failed to send private message: Sender was silenced'
        )
        return

    if target.silenced:
        sender.enqueue_silenced_target(target.name)
        return

    if target.client.friendonly_dms:
        if sender.id not in target.friends:
            sender.enqueue_blocked_dms(sender.name)
            return

    if (time.time() - sender.last_minute_stamp) > 60:
        sender.last_minute_stamp = time.time()
        sender.recent_message_count = 0

    if sender.recent_message_count > 35 and not sender.is_bot:
        sender.silence(60, reason='Chat spamming')
        return

    if (parsed_message := message.content.strip()).startswith('!') \
        or target == session.bot_player:
        # A command was executed
        commands.execute(sender, target, parsed_message)
        return

    # Limit message size
    if len(message.content) > 512:
        message.content = message.content[:512] + '... (truncated)'

    if target.away_message:
        sender.enqueue_message(
            bMessage(
                target.name,
                 f'\x01ACTION is away: {target.away_message}\x01',
                target.name,
                target.id,
                is_private=True
            )
        )

    target.enqueue_message(
        bMessage(
            sender.name,
            message.content,
            sender.name,
            sender.id,
            is_private=True
        )
    )

    sender.recent_message_count += 1
    sender.logger.info(f'[PM -> {target.name}]: {message.content}')

    messages.create(
        sender.name,
        target.name,
        message.content[:512]
    )

    sender.update_activity()

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
                session.bot_player.id,
                is_private=True
            )
        )
        return

    player.away_message = None
    player.enqueue_message(
        bMessage(
            session.bot_player.name,
            'You are no longer marked as being away',
            session.bot_player.name,
            session.bot_player.id,
            is_private=True
        )
    )

@register(RequestPacket.ADD_FRIEND)
def add_friend(player: Player, target_id: int):
    if not (target := session.players.by_id(target_id)):
        return

    if abs(target.id) in player.friends:
        return

    if target.id == player.id:
        # This is somehow possible in b1700
        return

    relationships.create(
        player.id,
        target_id
    )

    session.logger.info(f'{player.name} is now friends with {target.name}.')

    player.reload_object()
    player.enqueue_friends()

@register(RequestPacket.REMOVE_FRIEND)
def remove_friend(player: Player, target_id: int):
    if not (target := session.players.by_id(target_id)):
        return

    if abs(target.id) not in player.friends:
        return

    relationships.delete(
        player.id,
        target_id
    )

    session.logger.info(f'{player.name} is no longer friends with {target.name}.')

    player.reload_object()
    player.enqueue_friends()

@register(RequestPacket.BEATMAP_INFO)
def beatmap_info(player: Player, info: bBeatmapInfoRequest, ignore_limit: bool = False):
    maps: List[Tuple[int, DBBeatmap]] = []

    # Limit request filenames/ids
    if not ignore_limit:
        info.beatmap_ids = info.beatmap_ids[:100]
        info.filenames = info.filenames[:100]

    total_maps = len(info.beatmap_ids) + len(info.filenames)

    if total_maps <= 0:
        return

    player.logger.info(f'Got {total_maps} beatmap requests')

    # Fetch all matching beatmaps from database
    with session.database.managed_session() as s:
        filename_beatmaps = s.query(DBBeatmap) \
            .options(selectinload(DBBeatmap.beatmapset)) \
            .filter(DBBeatmap.filename.in_(info.filenames)) \
            .all()

        found_beatmaps = {
            beatmap.filename:beatmap
            for beatmap in filename_beatmaps
        }

        for index, filename in enumerate(info.filenames):
            if filename not in found_beatmaps:
                continue

            # The client will identify the beatmaps by their index
            # in the "beatmapInfoSendList" array for the filenames
            maps.append((
                index,
                found_beatmaps[filename]
            ))

        id_beatmaps = s.query(DBBeatmap) \
            .options(selectinload(DBBeatmap.beatmapset)) \
            .filter(DBBeatmap.id.in_(info.beatmap_ids)) \
            .all()

        for beatmap in id_beatmaps:
            # For the ids, the client doesn't require the index
            # and we can just set it to -1, so that it will lookup
            # the beatmap by its id
            maps.append((
                -1,
                beatmap
            ))

        # Create beatmap response
        map_infos: List[bBeatmapInfo] = []

        for index, beatmap in maps:
            if beatmap.status <= -3:
                # Not submitted
                continue

            ranked = {
                -3: -1, # Not submitted
                -2: 0,  # Graveyard: Pending
                -1: 0,  # WIP: Pending
                 0: 0,  # Pending: Pending
                 1: 1,  # Ranked: Ranked
                 2: 2,  # Approved: Approved
                 3: 2,  # Qualified: Approved
                 4: 2,  # Loved: Approved
            }[beatmap.status]

            # Get personal best in every mode for this beatmap
            grades = {
                0: Grade.N,
                1: Grade.N,
                2: Grade.N,
                3: Grade.N
            }

            for mode in range(4):
                grade = s.query(DBScore.grade) \
                    .filter(DBScore.beatmap_id == beatmap.id) \
                    .filter(DBScore.user_id == player.id) \
                    .filter(DBScore.mode == mode) \
                    .filter(DBScore.status == 3) \
                    .scalar()

                if grade:
                    grades[mode] = Grade[grade]

            map_infos.append(
                bBeatmapInfo(
                    index,
                    beatmap.id,
                    beatmap.set_id,
                    beatmap.beatmapset.topic_id or 0,
                    ranked,
                    grades[0], # Standard
                    grades[2], # Fruits
                    grades[1], # Taiko
                    grades[3], # Mania
                    beatmap.md5
                )
            )

        player.logger.info(
            f'Sending reply with {len(map_infos)} beatmaps'
        )

        player.send_packet(
            player.packets.BEATMAP_INFO_REPLY,
            bBeatmapInfoReply(map_infos)
        )

@register(RequestPacket.START_SPECTATING)
def start_spectating(player: Player, player_id: int):
    if player_id == player.id:
        player.logger.warning('Failed to start spectating: Player tried to spectate himself?')
        return

    if not (target := session.players.by_id(player_id)):
        player.logger.warning(f'Failed to start spectating: Player with id "{player_id}" was not found!')
        return

    if target.id == session.bot_player.id:
        player.logger.warning(f'Tried to spectate {session.bot_player.name}.')
        return

    if (player.spectating or player in target.spectators) and not player.is_tourney_client:
        stop_spectating(player)

    player.logger.info(f'Started spectating "{target.name}".')
    player.spectating = target

    # Join their channel
    player.enqueue_channel(target.spectator_chat.bancho_channel, autojoin=True)
    target.spectator_chat.add(player)

    # Enqueue fellow spectators
    for p in target.spectators:
        player.enqueue_fellow_spectator(p.id)
        p.enqueue_fellow_spectator(player.id)

    # Enqueue to target
    target.spectators.add(player)
    target.enqueue_spectator(player.id)
    target.enqueue_channel(target.spectator_chat.bancho_channel)

    # Check if target joined #spectator
    if target not in target.spectator_chat.users and not player.is_tourney_client:
        target.spectator_chat.add(target)

@register(RequestPacket.STOP_SPECTATING)
def stop_spectating(player: Player):
    if not player.spectating:
        player.logger.warning('Failed to stop spectating: Player is not spectating!')
        return

    if player in player.spectating.spectators:
        # Remove from target
        player.spectating.spectators.remove(player)

    # Leave spectator channel
    player.spectating.spectator_chat.remove(player)

    # Enqueue to others
    for p in player.spectating.spectators:
        p.enqueue_fellow_spectator_left(player.id)

    # Enqueue to target
    player.spectating.enqueue_spectator_left(player.id)

    # TODO: Kick from spectator channel if no spectators left?

    player.logger.info(f'Stopped spectating "{player.spectating.name}".')
    player.spectating = None

@register(RequestPacket.CANT_SPECTATE)
def cant_spectate(player: Player):
    if not player.spectating:
        return

    player.logger.info(f"Player is missing beatmap to spectate.")
    player.spectating.enqueue_cant_spectate(player.id)

    for p in player.spectating.spectators:
        p.enqueue_cant_spectate(player.id)

@register(RequestPacket.SEND_FRAMES)
def send_frames(player: Player, bundle: bReplayFrameBundle):
    if not player.spectators:
        return

    for p in player.spectators:
        p.enqueue_frames(bundle)

@register(RequestPacket.JOIN_LOBBY)
def join_lobby(player: Player):
    for p in session.players:
        p.enqueue_lobby_join(player.id)

    player.in_lobby = True

    for match in session.matches.active:
        player.enqueue_match(match.bancho_match)

@register(RequestPacket.PART_LOBBY)
def part_lobby(player: Player):
    player.in_lobby = False

    for p in session.players:
        p.enqueue_lobby_part(player.id)

@register(RequestPacket.MATCH_INVITE)
def invite(player: Player, target_id: int):
    if player.silenced:
        return

    if not player.match:
        return

    if not (target := session.players.by_id(target_id)):
        return

    # TODO: Check invite spams
    target.enqueue_invite(
        bMessage(
            player.name,
            f'Come join my multiplayer match: {player.match.embed}',
            player.name,
            player.id,
            is_private=True
        )
    )

@register(RequestPacket.CREATE_MATCH)
def create_match(player: Player, bancho_match: bMatch):
    if not player.in_lobby:
        player.logger.warning('Tried to create match, but not in lobby')
        player.enqueue_matchjoin_fail()
        return

    if player.is_tourney_client:
        player.logger.warning('Tried to create match, but was inside tourney client')
        player.enqueue_matchjoin_fail()
        return

    if player.silenced:
        player.logger.warning('Tried to create match, but was silenced')
        player.enqueue_matchjoin_fail()
        return

    if player.match:
        player.logger.warning('Tried to create match, but was already inside one')
        player.enqueue_matchjoin_fail()
        player.match.kick_player(player)
        return

    match = Match.from_bancho_match(bancho_match, player)

    # Limit match name
    match.name = match.name[:50]

    if not session.matches.append(match):
        player.logger.warning('Failed to append match to collection')
        player.enqueue_matchjoin_fail()
        return

    for index, slot in enumerate(bancho_match.slots):
        match.slots[index].status = slot.status

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

    match.db_match = matches.create(
        match.name,
        match.id,
        match.host.id
    )

    session.logger.info(f'Created match: "{match.name}"')

    join_match(
        player,
        bMatchJoin(
            match.id,
            match.password
        )
    )

    match.chat.send_message(
        session.bot_player,
        f"Match history available [http://osu.{config.DOMAIN_NAME}/mp/{match.db_match.id} here].",
        ignore_privs=True
    )

@register(RequestPacket.JOIN_MATCH)
def join_match(player: Player, match_join: bMatchJoin):
    if not session.matches.exists(match_join.match_id):
        player.logger.warning(f'{player.name} tried to join a match that does not exist')
        player.enqueue_matchjoin_fail()
        player.enqueue_match_disband(match_join.match_id)
        return

    match = session.matches[match_join.match_id]
    match.last_activity = time.time()

    if player.is_tourney_client:
        player.logger.warning('Tried to join match, but was inside tourney client')
        player.enqueue_matchjoin_fail()
        return

    if player.match:
        # Player already joined a match
        player.logger.warning(f'{player.name} tried to join a match, but is already inside one')
        player.enqueue_matchjoin_fail()
        player.match.kick_player(player)
        return

    if (player.id in match.banned_players) and not player.is_admin:
        player.logger.warning(f'{player.name} tried to join a match, but was banned from it')
        player.enqueue_matchjoin_fail()
        return

    if player is not match.host:
        if match_join.password != match.password:
            # Invalid password
            player.logger.warning('Failed to join match: Invalid password')
            player.enqueue_matchjoin_fail()
            return

        if (slot_id := match.get_free()) is None:
            # Match is full
            player.logger.warning('Failed to join match: Match full')
            player.enqueue_matchjoin_fail()
            return
    else:
        # Player is creating the match
        slot_id = 0

    # Join the chat
    player.enqueue_channel(match.chat.bancho_channel, autojoin=True)
    match.chat.add(player)

    slot = match.slots[slot_id]

    if match.team_type in (MatchTeamTypes.TeamVs, MatchTeamTypes.TagTeamVs):
        slot.team = SlotTeam.Red

    slot.status = SlotStatus.NotReady
    slot.player = player

    player.match = match
    player.enqueue_matchjoin_success(match.bancho_match)

    events.create(
        match.db_match.id,
        type=EventType.Join,
        data={
            'user_id': player.id,
            'name': player.name
        }
    )

    match.logger.info(f'{player.name} joined')
    match.update()

@register(RequestPacket.LEAVE_MATCH)
def leave_match(player: Player):
    if not player.match:
        return

    player.match.last_activity = time.time()

    if not (slot := player.match.get_slot(player)):
        return

    status = (
        SlotStatus.Locked
        if slot.status == SlotStatus.Locked
        else SlotStatus.Open
    )

    slot.reset(status)

    channel_leave(
        player,
        player.match.chat.name,
        kick=True
    )

    events.create(
        player.match.db_match.id,
        type=EventType.Leave,
        data={
            'user_id': player.id,
            'name': player.name
        }
    )

    if (player is player.match.host and player.match.beatmap_id == -1):
        # Host was choosing beatmap; reset beatmap to previous
        player.match.beatmap_id = player.match.previous_beatmap_id
        player.match.beatmap_hash = player.match.previous_beatmap_hash
        player.match.beatmap_name = player.match.previous_beatmap_name

    if all(slot.empty for slot in player.match.slots):
        # No players in match anymore -> Disband match
        player.enqueue_match_disband(player.match.id)

        for p in session.players.in_lobby:
            p.enqueue_match_disband(player.match.id)

        session.matches.remove(player.match)
        player.match.starting = None

        match_id = player.match.db_match.id

        last_game = events.fetch_last_by_type(
            match_id,
            type=EventType.Result
        )

        if not last_game:
            # No games were played
            matches.delete(match_id)
        else:
            matches.update(match_id, {'ended_at': datetime.now()})
            events.create(match_id, type=EventType.Disband)

        player.match.logger.info('Match was disbanded.')
        player.match = None
        return

    if player is player.match.host:
        # Player was host, transfer to next player
        for slot in player.match.slots:
            if slot.status.value & SlotStatus.HasPlayer.value:
                player.match.host = slot.player
                player.match.host.enqueue_match_transferhost()

        events.create(
            player.match.db_match.id,
            type=EventType.Host,
            data={
                'previous': {'id': player.id, 'name': player.name},
                'new': {'id': player.match.host.id, 'name': player.match.host.name}
            }
        )

    player.match.update()
    player.match = None

@register(RequestPacket.MATCH_CHANGE_SLOT)
def change_slot(player: Player, slot_id: int):
    if not player.match:
        return

    if not 0 <= slot_id < config.MULTIPLAYER_MAX_SLOTS:
        return

    if player.match.slots[slot_id].status != SlotStatus.Open:
        return

    player.match.last_activity = time.time()

    if not (slot := player.match.get_slot(player)):
        return

    player.match.slots[slot_id].copy_from(slot)
    slot.reset()

    player.match.update()

@register(RequestPacket.MATCH_CHANGE_SETTINGS)
def change_settings(player: Player, match: bMatch):
    if not player.match:
        return

    if player is not player.match.host:
        return

    player.match.last_activity = time.time()

    player.match.change_settings(match)

@register(RequestPacket.MATCH_CHANGE_BEATMAP)
def change_beatmap(player: Player, new_match: bMatch):
    if not (match := player.match):
        return

    if player is not player.match.host:
        return

    player.match.last_activity = time.time()

    # New map has been chosen
    match.logger.info(f'Selected: {new_match.beatmap_text}')
    match.unready_players()

    # Unready players with no beatmap
    match.unready_players(SlotStatus.NoMap)

    # Lookup beatmap in database
    beatmap = beatmaps.fetch_by_checksum(new_match.beatmap_checksum)

    if beatmap:
        match.beatmap_id   = beatmap.id
        match.beatmap_hash = beatmap.md5
        match.beatmap_name = beatmap.full_name
        match.mode         = GameMode(beatmap.mode)
        beatmap_text       = beatmap.link
    else:
        match.beatmap_id   = new_match.beatmap_id
        match.beatmap_hash = new_match.beatmap_checksum
        match.beatmap_name = new_match.beatmap_text
        match.mode         = new_match.mode
        beatmap_text       = new_match.beatmap_text

    match.chat.send_message(
        session.bot_player,
        f'Selected: {beatmap_text}'
    )

    match.update()

@register(RequestPacket.MATCH_CHANGE_MODS)
def change_mods(player: Player, mods: Mods):
    if not player.match:
        return

    player.match.last_activity = time.time()

    mods_before = copy(player.match.mods)

    if player.match.freemod:
        if player is player.match.host:
            # Only keep SpeedMods
            player.match.mods = mods & Mods.SpeedMods

            # There is a bug, where DT and NC are enabled at the same time
            if Mods.DoubleTime|Mods.Nightcore in player.match.mods:
                player.match.mods &= ~Mods.DoubleTime

        if slot := player.match.get_slot(player):
            # Only keep mods that are "FreeModAllowed"
            slot.mods = mods & Mods.FreeModAllowed

            player.match.logger.info(
                f'{player.name} changed their mods to {slot.mods.short}'
            )
    else:
        if player is not player.match.host:
            player.logger.warning(f'{player.name} tried to change mods, but was not host')
            return

        player.match.mods = mods

        # There is a bug, where DT and NC are enabled at the same time
        if Mods.DoubleTime|Mods.Nightcore in player.match.mods:
            player.match.mods &= ~Mods.DoubleTime

        player.match.logger.info(f'Changed mods to: {player.match.mods.short}')

    mods_changed = player.match.mods != mods_before

    if mods_changed:
        player.match.unready_players()

    player.match.update()

@register(RequestPacket.MATCH_READY)
def ready(player: Player):
    if not player.match:
        return

    player.match.last_activity = time.time()

    if not (slot := player.match.get_slot(player)):
        return

    slot.status = SlotStatus.Ready
    player.match.update()

@register(RequestPacket.MATCH_HAS_BEATMAP)
@register(RequestPacket.MATCH_NOT_READY)
def not_ready(player: Player):
    if not player.match:
        return

    player.match.last_activity = time.time()

    if not (slot := player.match.get_slot(player)):
        return

    slot.status = SlotStatus.NotReady
    player.match.update()

@register(RequestPacket.MATCH_NO_BEATMAP)
def no_beatmap(player: Player):
    if not player.match:
        return

    player.match.last_activity = time.time()

    if player.match.beatmap_id <= 0:
        # Beatmap is being selected by the host
        return

    if not (slot := player.match.get_slot(player)):
        return

    slot.status = SlotStatus.NoMap
    player.match.update()

@register(RequestPacket.MATCH_LOCK)
def lock(player: Player, slot_id: int):
    if not player.match:
        return

    if player is not player.match.host:
        return

    player.match.last_activity = time.time()

    if not 0 <= slot_id < config.MULTIPLAYER_MAX_SLOTS:
        return

    slot = player.match.slots[slot_id]

    if slot.player is player:
        # Player can't kick themselves
        return

    if slot.has_player:
        player.match.kick_player(slot.player)

    slot.status = (
        SlotStatus.Open
        if slot.status == SlotStatus.Locked
        else SlotStatus.Locked
    )

    player.match.update()

@register(RequestPacket.MATCH_CHANGE_TEAM)
def change_team(player: Player):
    if not player.match:
        return

    if not player.match.ffa:
        return

    player.match.last_activity = time.time()

    if not (slot := player.match.get_slot(player)):
        return

    slot.team = {
        SlotTeam.Blue: SlotTeam.Red,
        SlotTeam.Red: SlotTeam.Blue
    }[slot.team]

    player.match.update()

@register(RequestPacket.MATCH_TRANSFER_HOST)
def transfer_host(player: Player, slot_id: int):
    if not player.match:
        return

    if player is not player.match.host:
        return

    player.match.last_activity = time.time()

    if not 0 <= slot_id < config.MULTIPLAYER_MAX_SLOTS:
        return

    if not (target := player.match.slots[slot_id].player):
        player.match.logger.warning('Host tried to transfer host into an empty slot?')
        return

    if target is player.match.host:
        player.match.host.enqueue_match_transferhost()
        return

    player.match.host = target
    player.match.host.enqueue_match_transferhost()

    events.create(
        player.match.db_match.id,
        type=EventType.Host,
        data={
            'new': {'id': target.id, 'name': target.name},
            'previous': {'id': player.id, 'name': player.name}
        }
    )

    player.match.logger.info(f'Changed host to: {target.name}')
    player.match.update()

@register(RequestPacket.MATCH_CHANGE_PASSWORD)
def change_password(player: Player, new_password: str):
    if not player.match:
        return

    if player is not player.match.host:
        return

    player.match.password = new_password
    player.match.update()

    player.match.logger.info(
        f'Changed password to: {new_password}'
    )

@register(RequestPacket.MATCH_START)
def match_start(player: Player):
    if not player.match:
        return

    player.match.last_activity = time.time()

    if player is not player.match.host:
        return

    player.match.start()

@register(RequestPacket.MATCH_LOAD_COMPLETE)
def load_complete(player: Player):
    if not player.match:
        return

    if not player.match.in_progress:
        return

    if not (slot := player.match.get_slot(player)):
        return

    slot.loaded = True

    if all(player.match.loaded_players):
        for slot in player.match.slots:
            if not slot.has_map:
                continue

            slot.player.enqueue_match_all_players_loaded()

        player.match.update()

@register(RequestPacket.MATCH_SKIP)
def skip(player: Player):
    if not player.match:
        return

    if not player.match.in_progress:
        return

    slot, id = player.match.get_slot_with_id(player)

    if not slot:
        return

    slot.skipped = True

    for p in player.match.players:
        p.enqueue_player_skipped(id)

    for slot in player.match.slots:
        if slot.status == SlotStatus.Playing and not slot.skipped:
            return

    for p in player.match.players:
        p.enqueue_match_skip()

@register(RequestPacket.MATCH_FAILED)
def player_failed(player: Player):
    if not player.match:
        return

    if not player.match.in_progress:
        return

    slot, slot_id = player.match.get_slot_with_id(player)
    assert slot_id is not None

    slot.has_failed = True

    for p in player.match.players:
        p.enqueue_player_failed(slot_id)

@register(RequestPacket.MATCH_SCORE_UPDATE)
def score_update(player: Player, scoreframe: bScoreFrame):
    if not player.match:
        return

    slot, id = player.match.get_slot_with_id(player)

    if not slot:
        return

    if not slot.is_playing:
        return

    slot.last_frame = scoreframe
    scoreframe.id = id

    reactor.callFromThread(
        player.match.process_score_update,
        scoreframe
    )

@register(RequestPacket.MATCH_COMPLETE)
def match_complete(player: Player):
    if not player.match:
        return

    if not player.match.in_progress:
        return

    player.match.last_activity = time.time()

    if not (slot := player.match.get_slot(player)):
        return

    slot.status = SlotStatus.Complete

    if any([slot.is_playing for slot in player.match.slots]):
        return

    player.match.finish()

@register(RequestPacket.TOURNAMENT_MATCH_INFO)
def tourney_match_info(player: Player, match_id: int):
    if not player.is_supporter:
        player.logger.warning('Tried to request tourney match info, but was not supporter.')
        return

    if not player.is_tourney_client:
        player.logger.warning('Tried to request tourney match info, but was not in tourney client.')
        return

    player.logger.debug(f'Requesting tourney match info ({match_id})')

    if not (db_match := matches.fetch_by_id(match_id)):
        player.logger.warning(f'Tried to request tourney match info, but match with id "{match_id}" was not found.')
        return

    if db_match.ended_at != None:
        player.logger.warning('Tried to request tourney match info, but match has already ended.')
        return

    if not session.matches.exists(db_match.bancho_id):
        player.logger.warning('Tried to request tourney match info, but match was not found in active matches.')
        return

    match = session.matches[db_match.bancho_id]

    player.logger.debug(f'Got tournament match info request for "{match.name}".')
    player.enqueue_match(match.bancho_match)

@register(RequestPacket.ERROR_REPORT)
def bancho_error(player: Player, error: str):
    session.logger.error(f'Bancho Error Report:\n{error}')
    officer.call(f'Bancho Error Report:\n```c#\n{error}```')

@register(RequestPacket.CHANGE_FRIENDONLY_DMS)
def change_friendonly_dms(player: Player, enabled: bool):
    player.client.friendonly_dms = enabled
