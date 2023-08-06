
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
    bScoreFrame,
    bMatchJoin,
    bMessage,
    bMatch
)

from ..common.constants import (
    MatchTeamTypes,
    PresenceFilter,
    SlotStatus,
    SlotTeam,
    Grade,
    Mods
)

from typing import Callable, Tuple, List
from copy import copy

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
    try:
        if channel_name == '#spectator':
            if player.spectating:
                channel_name = player.spectating.spectator_chat.name
            else:
                channel_name = player.spectator_chat.name

        elif channel_name == '#multiplayer':
            channel_name = player.match.chat.name
    except AttributeError:
        player.revoke_channel(channel_name)

    if not (channel := session.channels.by_name(channel_name)):
        player.revoke_channel(channel_name)
        return

    channel.add(player)

@register(RequestPacket.LEAVE_CHANNEL)
def channel_leave(player: Player, channel_name: str, kick: bool = False):
    try:
        if channel_name == '#spectator':
            if player.spectating:
                channel_name = player.spectating.spectator_chat.name
            else:
                channel_name = player.spectator_chat.name

        elif channel_name == '#multiplayer':
            channel_name = player.match.chat.name
    except AttributeError:
        player.revoke_channel(channel_name)

    if not (channel := session.channels.by_name(channel_name)):
        player.revoke_channel(channel_name)
        return

    if kick:
        player.revoke_channel(channel_name)

    channel.remove(player)

@register(RequestPacket.SEND_MESSAGE)
def send_message(player: Player, message: bMessage):
    try:
        if message.target == '#spectator':
            if player.spectating:
                message.target = player.spectating.spectator_chat.name
            else:
                message.target = player.spectator_chat.name

        elif message.target == '#multiplayer':
            message.target = player.match.chat.name
    except AttributeError:
        player.revoke_channel(message.target)

    if not (channel := session.channels.by_name(message.target)):
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
            player.id
        )
    )

@register(RequestPacket.CREATE_MATCH)
def create_match(player: Player, bancho_match: bMatch):
    if not player.in_lobby:
        player.logger.warning('Tried to create match, but not in lobby')
        player.enqueue_matchjoin_fail()
        return

    if player.silenced:
        player.logger.warning('Tried to create match, but was silenced')
        player.enqueue_matchjoin_fail()
        return

    if player.match:
        print(player.match)
        player.logger.warning('Tried to create match, but was already inside one')
        player.enqueue_matchjoin_fail()
        return

    match = Match.from_bancho_match(bancho_match)

    if not session.matches.append(match):
        player.logger.warning('Tried to create match, but max match limit was reached')
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
        player.logger.warning(f'{player.name} tried to join a match that does not exist')
        player.enqueue_matchjoin_fail()
        player.enqueue_match_disband(match_join.match_id)
        return

    if player.match:
        # Player already joined the match
        player.logger.warning(f'{player.name} tried to join a match, but is already inside one')
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
    player.enqueue_channel(match.chat.bancho_channel)

    slot = match.slots[slot_id]

    if match.team_type in (MatchTeamTypes.TeamVs, MatchTeamTypes.TagTeamVs):
        slot.team = SlotTeam.Red

    slot.status = SlotStatus.NotReady
    slot.player = player

    player.match = match
    player.enqueue_matchjoin_success(match.bancho_match)

    match.logger.info(f'{player.name} joined')
    match.update()

@register(RequestPacket.LEAVE_MATCH)
def leave_match(player: Player):
    if not player.match:
        return

    slot = player.match.get_slot(player)
    assert slot is not None

    if slot.status == SlotStatus.Locked:
        status = SlotStatus.Locked
    else:
        status = SlotStatus.Open

    slot.reset(status)
    channel_leave(
        player,
        player.match.chat.name,
        kick=True
    )

    if all(slot.empty for slot in player.match.slots):
        player.enqueue_match_disband(player.match.id)

        for p in session.players.in_lobby:
            p.enqueue_match_disband(player.match.id)

        # Match is empty
        session.matches.remove(player.match)
    else:
        if player is player.match.host:
            # Player was host, transfer to next player
            for slot in player.match.slots:
                if slot.status.value & SlotStatus.HasPlayer.value:
                    player.match.host = slot.player
                    player.match.host.enqueue_match_transferhost()

        player.match.update()

    player.match = None

@register(RequestPacket.MATCH_CHANGE_SLOT)
def change_slot(player: Player, slot_id: int):
    if not player.match:
        return

    if not 0 <= slot_id < 8:
        return

    if player.match.slots[slot_id].status != SlotStatus.Open:
        return

    slot = player.match.get_slot(player)
    assert slot is not None

    player.match.slots[slot_id].copy_from(slot)
    slot.reset()

    player.match.update()

@register(RequestPacket.MATCH_CHANGE_SETTINGS)
def change_settings(player: Player, match: bMatch):
    if not player.match:
        return

    if player is not player.match.host:
        return

    player.match.change_settings(match)

@register(RequestPacket.MATCH_CHANGE_MODS)
def change_mods(player: Player, mods: Mods):
    if not player.match:
        return

    mods_before = copy(player.match.mods)

    if player.match.freemod:
        if player is player.match.host:
            # Onky keep SpeedMods
            player.match.mods = mods & Mods.SpeedMods

            # There is a bug, where DT and NC are enabled at the same time
            if Mods.DoubleTime|Mods.Nightcore in player.match.mods:
                player.match.mods &= ~Mods.DoubleTime

        slot = player.match.get_slot(player)
        assert slot is not None

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

    slot = player.match.get_slot(player)
    assert slot is not None

    slot.status = SlotStatus.Ready
    player.match.update()

@register(RequestPacket.MATCH_HAS_BEATMAP)
@register(RequestPacket.MATCH_NOT_READY)
def not_ready(player: Player):
    if not player.match:
        return

    slot = player.match.get_slot(player)
    assert slot is not None

    slot.status = SlotStatus.NotReady
    player.match.update()

@register(RequestPacket.MATCH_NO_BEATMAP)
def not_beatmap(player: Player):
    if not player.match:
        return

    slot = player.match.get_slot(player)
    assert slot is not None

    slot.status = SlotStatus.NoMap
    player.match.update()

@register(RequestPacket.MATCH_LOCK)
def lock(player: Player, slot_id: int):
    if not player.match:
        return

    if player is not player.match.host:
        return

    if not 0 <= slot_id < 8:
        return

    slot = player.match.slots[slot_id]

    if slot.player is player:
        # Player can't kick themselves
        player.match.logger.warning(f'{player.name} tried to kick himself?')
        return

    if slot.has_player:
        player.match.kick_player(slot.player)

    if slot.status == SlotStatus.Locked:
        slot.status = SlotStatus.Open
    else:
        slot.status = SlotStatus.Locked

    player.match.update()

@register(RequestPacket.MATCH_CHANGE_TEAM)
def change_team(player: Player):
    if not player.match:
        return

    if not player.match.ffa:
        return

    slot = player.match.get_slot(player)
    assert slot is not None

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

    if not 0 <= slot_id < 8:
        return

    if not (target := player.match.slots[slot_id].player):
        player.match.logger.warning('Host tried to transfer host into an empty slot?')
        return

    player.match.host = target
    player.match.host.enqueue_match_transferhost()

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

    if player is not player.match.host:
        return

    player.match.start()

@register(RequestPacket.MATCH_LOAD_COMPLETE)
def load_complete(player: Player):
    if not player.match:
        return

    if not player.match.in_progress:
        return

    slot = player.match.get_slot(player)
    assert slot is not None

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
    assert slot is not None

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

    slot_id = player.match.get_slot_id(player)
    assert slot_id is not None

    for p in player.match.players:
        p.enqueue_player_failed(slot_id)

@register(RequestPacket.MATCH_SCORE_UPDATE)
def score_update(player: Player, scoreframe: bScoreFrame):
    if not player.match:
        return

    slot, id = player.match.get_slot_with_id(player)
    assert slot is not None

    if not slot.is_playing:
        return

    scoreframe.id = id

    for p in player.match.players:
        p.enqueue_score_update(scoreframe)

    for p in session.players.in_lobby:
        p.enqueue_score_update(scoreframe)

@register(RequestPacket.MATCH_COMPLETE)
def match_complete(player: Player):
    if not player.match:
        return

    if not player.match.in_progress:
        return

    slot = player.match.get_slot(player)
    assert slot is not None

    slot.status = SlotStatus.Complete

    if any([slot.is_playing for slot in player.match.slots]):
        return

    # Players that have been playing this round
    players = [
        slot.player for slot in player.match.slots
        if slot.status.value & SlotStatus.Complete.value
        and slot.has_player
    ]

    player.match.unready_players(SlotStatus.Complete)
    player.match.in_progress = False

    for p in players:
        p.enqueue_match_complete()

    player.match.logger.info('Match finished')
    player.match.update()

@register(RequestPacket.CHANGE_FRIENDONLY_DMS)
def change_friendonly_dms(player: Player, enabled: bool):
    player.client.friendonly_dms = enabled
