

from twisted.internet import reactor
from datetime import datetime
from typing import Callable
from copy import copy
from chio import (
    SlotStatus,
    ScoreFrame,
    PacketType,
    MatchJoin,
    TeamType,
    SlotTeam,
    Message,
    Mods
)

from app.handlers.osu.chat import channel_leave
from app.common.database import beatmaps, matches, events
from app.common.constants import GameMode, EventType
from app.objects.channel import MultiplayerChannel
from app.objects.multiplayer import Match
from app.clients.osu import OsuClient
from app import session

import logging
import config
import time

def register(packet: PacketType) -> Callable:
    def wrapper(func) -> Callable:
        session.osu_handlers[packet] = func
        return func
    return wrapper

@register(PacketType.OsuLobbyJoin)
def join_lobby(client: OsuClient):
    for p in session.players.osu_clients:
        p.enqueue_packet(PacketType.BanchoLobbyJoin, client.id)

    session.players.osu_in_lobby.add(client)
    client.in_lobby = True

    for match in session.matches.active:
        client.enqueue_packet(PacketType.BanchoMatchNew, match)

@register(PacketType.OsuLobbyPart)
def part_lobby(client: OsuClient):
    session.players.osu_in_lobby.discard(client)
    client.in_lobby = False

    for p in session.players.osu_clients:
        p.enqueue_packet(PacketType.BanchoLobbyPart, client.id)

@register(PacketType.OsuInvite)
def invite(client: OsuClient, target_id: int):
    if client.silenced:
        return

    if not client.match:
        return

    if not (target := session.players.by_id(target_id)):
        return

    if target.is_irc or target.is_tourney_client:
        return

    if target.match is client.match:
        return

    if not target.invite_limiter.allow():
        client.logger.warning(f'Tried to invite {target.name}, but was rate-limited.')
        client.enqueue_message(
            'You are inviting too fast. Slow down.',
            session.banchobot,
            session.banchobot.name
        )
        return

    target.enqueue_packet(
        PacketType.BanchoInvite,
        Message(
            client.name,
            f'Come join my multiplayer match: {client.match.embed}',
            client.name,
            client.id
        )
    )

@register(PacketType.OsuMatchCreate)
def create_match(client: OsuClient, bancho_match: Match):
    if not client.in_lobby:
        client.logger.warning('Tried to create match, but not in lobby')
        client.enqueue_packet(PacketType.BanchoMatchJoinFail)
        return

    if client.is_tourney_client:
        client.logger.warning('Tried to create match, but was inside tourney client')
        client.enqueue_packet(PacketType.BanchoMatchJoinFail)
        return

    if client.silenced:
        client.logger.warning('Tried to create match, but was silenced')
        client.enqueue_packet(PacketType.BanchoMatchJoinFail)
        return

    if client.match:
        client.logger.warning('Tried to create match, but was already inside one')
        client.enqueue_packet(PacketType.BanchoMatchJoinFail)
        client.match.kick_player(client)
        return

    match = Match.from_bancho_match(bancho_match, client)

    # Limit match name
    match.name = match.name[:50]

    if not session.matches.append(match):
        client.logger.warning('Failed to append match to collection')
        client.enqueue_packet(PacketType.BanchoMatchJoinFail)
        return

    for index, slot in enumerate(bancho_match.slots):
        match.slots[index].status = slot.status

    match.logger = logging.getLogger(f'multi_{match.id}')
    match.chat = MultiplayerChannel(match)
    session.channels.add(match.chat)

    match.db_match = matches.create(
        match.name,
        match.id,
        match.host_id
    )

    session.logger.info(f'Created match: "{match.name}"')

    join_match(
        client,
        MatchJoin(
            match.id,
            match.password
        )
    )

    match.chat.send_message(
        session.banchobot,
        f"Match history available [http://osu.{config.DOMAIN_NAME}/mp/{match.db_match.id} here]."
    )

@register(PacketType.OsuMatchJoin)
def join_match(client: OsuClient, match_join: MatchJoin):
    if not session.matches.exists(match_join.match_id):
        client.logger.warning(f'{client.name} tried to join a match that does not exist')
        client.enqueue_packet(PacketType.BanchoMatchDisband, match_join.match_id)
        client.enqueue_packet(PacketType.BanchoMatchJoinFail)
        return

    match = session.matches[match_join.match_id]
    match.last_activity = time.time()

    if client.is_tourney_client:
        client.logger.warning('Tried to join match, but was inside tourney client')
        client.enqueue_packet(PacketType.BanchoMatchJoinFail)
        return

    if client.match:
        # Player already joined a match
        client.logger.warning(f'{client.name} tried to join a match, but is already inside one')
        client.enqueue_packet(PacketType.BanchoMatchJoinFail)
        client.match.kick_player(client)
        return

    if (client.id in match.banned_players) and not client.is_admin:
        client.logger.warning(f'{client.name} tried to join a match, but was banned from it')
        client.enqueue_packet(PacketType.BanchoMatchJoinFail)
        return

    if client is not match.host:
        if match_join.password != match.password:
            # Invalid password
            client.logger.warning('Failed to join match: Invalid password')
            client.enqueue_packet(PacketType.BanchoMatchJoinFail)
            return

        if (slot_id := match.get_free()) is None:
            # Match is full
            client.logger.warning('Failed to join match: Match full')
            client.enqueue_packet(PacketType.BanchoMatchJoinFail)
            return
    else:
        # Player is creating the match
        slot_id = 0

    channel_object = match.chat.bancho_channel
    slot = match.slots[slot_id]

    if match.team_type in (TeamType.TeamVs, TeamType.TagTeamVs):
        slot.team = SlotTeam.Red

    slot.status = SlotStatus.NotReady
    slot.player = client

    if client.id in match.referee_players:
        # Make sure referee client joined the channel
        channel_object.name = match.chat.name
        client.referee_matches.add(match)

    if not match.host and client.id in match.referee_players:
        # This client has referee privileges, so we can make them the host
        match.host = client

    client.match = match
    client.enqueue_packet(PacketType.BanchoMatchJoinSuccess, match)

    match.logger.info(f'{client.name} joined')
    match.update()

    # Join the chat
    client.enqueue_channel(channel_object, autojoin=True)
    match.chat.add(client)

    match.send_referee_message(
        f"{client.name} joined in slot {slot_id + 1}.",
        session.banchobot
    )

    if client.id in match.referee_players:
        # Force-revoke #multiplayer
        client.enqueue_channel_revoked('#multiplayer')

    for client in session.players.osu_tournament_clients:
        # Ensure that all tourney clients got the client's presence
        client.enqueue_presence(client)
        client.enqueue_stats(client)

    events.create(
        match.db_match.id,
        type=EventType.Join,
        data={
            'user_id': client.id,
            'name': client.name
        }
    )

@register(PacketType.OsuMatchPart)
def leave_match(client: OsuClient):
    if not client.match:
        return

    client.match.last_activity = time.time()

    if not (slot := client.match.get_slot(client)):
        return

    status = (
        SlotStatus.Locked
        if slot.status == SlotStatus.Locked
        else SlotStatus.Open
    )

    slot.reset(status)

    if client.id not in client.match.referee_players:
        channel_leave(
            client,
            client.match.chat.display_name,
            kick=True
        )

    events.create(
        client.match.db_match.id,
        type=EventType.Leave,
        data={
            'user_id': client.id,
            'name': client.name
        }
    )

    if (client is client.match.host and client.match.beatmap_id == -1):
        # Host was choosing beatmap; reset beatmap to previous
        client.match.beatmap_id = client.match.previous_beatmap_id
        client.match.beatmap_checksum = client.match.previous_beatmap_hash
        client.match.beatmap_text = client.match.previous_beatmap_name

    if all(slot.empty for slot in client.match.slots) and not client.match.persistent:
        # No players in match anymore -> Disband match
        client.enqueue_packet(PacketType.BanchoMatchDisband, client.match.id)

        for p in session.players.osu_in_lobby:
            p.enqueue_packet(PacketType.BanchoMatchDisband, client.match.id)

        session.channels.remove(client.match.chat)
        session.matches.remove(client.match)
        client.match.starting = None

        match_id = client.match.db_match.id

        # Fetch last game event
        last_game = events.fetch_last_by_type(
            match_id,
            type=EventType.Result
        )

        if not last_game:
            # No games were played -> delete match
            matches.delete(match_id)
        else:
            matches.update(match_id, {'ended_at': datetime.now()})
            events.create(match_id, type=EventType.Disband)

        if not client.match:
            return

        client.match.logger.info('Match was disbanded.')
        client.match = None
        return

    if client.match.persistent and client is client.match.host:
        # This match has referee players, so we don't need a host
        client.match.host = None

    elif client is client.match.host:
        # Player was host, transfer to next client
        for slot in client.match.slots:
            if slot.status.value & SlotStatus.HasPlayer.value:
                client.match.host = slot.player
                client.match.host.enqueue_packet(PacketType.BanchoMatchTransferHost)

        events.create(
            client.match.db_match.id,
            type=EventType.Host,
            data={
                'previous': {'id': client.id, 'name': client.name},
                'new': {'id': client.match.host_id, 'name': client.match.host.name}
            }
        )

    if client.id not in client.match.referee_players:
        client.match.chat.remove(client)

    client.match.send_referee_message(
        f"{client.name} left the game.",
        session.banchobot
    )

    client.match.update()
    client.match = None

@register(PacketType.OsuMatchChangeSlot)
def change_slot(client: OsuClient, slot_id: int):
    if not client.match:
        return

    if not 0 <= slot_id < config.MULTIPLAYER_MAX_SLOTS:
        return

    if client.match.slots[slot_id].status != SlotStatus.Open:
        return

    client.match.last_activity = time.time()

    if not (slot := client.match.get_slot(client)):
        return

    client.match.slots[slot_id].copy_from(slot)
    slot.reset()

    client.match.update()
    client.match.send_referee_message(
        f'{client.name} moved to slot {slot_id + 1}.',
        session.banchobot
    )

@register(PacketType.OsuMatchChangeSettings)
def change_settings(client: OsuClient, match: Match):
    if not client.match:
        return

    if client is not client.match.host:
        return

    client.match.last_activity = time.time()
    client.match.change_settings(match)

@register(PacketType.OsuMatchChangeBeatmap)
def change_beatmap(client: OsuClient, new_match: Match):
    if not (match := client.match):
        return

    if client is not client.match.host:
        return

    client.match.last_activity = time.time()

    # New map has been chosen
    match.logger.info(f'Selected: {new_match.beatmap_text}')
    match.unready_players()

    # Unready players with no beatmap
    match.unready_players(SlotStatus.NoMap)

    # Lookup beatmap in database
    beatmap = beatmaps.fetch_by_checksum(new_match.beatmap_checksum)

    if beatmap:
        match.beatmap_id       = beatmap.id
        match.beatmap_checksum = beatmap.md5
        match.beatmap_text     = beatmap.full_name
        match.mode             = GameMode(beatmap.mode)
        beatmap_text           = beatmap.link
    else:
        match.beatmap_id       = new_match.beatmap_id
        match.beatmap_checksum = new_match.beatmap_checksum
        match.beatmap_text     = new_match.beatmap_text
        match.mode             = new_match.mode
        beatmap_text           = new_match.beatmap_text

    match.chat.send_message(
        session.banchobot,
        f'Selected: {beatmap_text}'
    )

    match.update()

@register(PacketType.OsuMatchChangeMods)
def change_mods(client: OsuClient, mods: Mods):
    if not client.match:
        return

    client.match.last_activity = time.time()

    # Convert chio mods
    mods = Mods(mods.value)
    mods_before = copy(client.match.mods)

    if client.match.freemod:
        if client is client.match.host:
            # Only keep SpeedMods
            client.match.mods = mods & Mods.SpeedMods

            # There is a bug, where DT and NC are enabled at the same time
            if Mods.DoubleTime|Mods.Nightcore in client.match.mods:
                client.match.mods &= ~Mods.DoubleTime

        if slot := client.match.get_slot(client):
            # Only keep mods that are "FreeModAllowed"
            slot.mods = mods & Mods.FreeModAllowed

            client.match.logger.info(
                f'{client.name} changed their mods to {slot.mods.short}'
            )
            client.match.send_referee_message(
                f'{client.name} changed their mods to {slot.mods.short}',
                session.banchobot
            )
    else:
        if client is not client.match.host:
            client.logger.warning(f'{client.name} tried to change mods, but was not host')
            return

        client.match.mods = mods

        # There is a bug, where DT and NC are enabled at the same time
        if Mods.DoubleTime|Mods.Nightcore in client.match.mods:
            client.match.mods &= ~Mods.DoubleTime

        client.match.logger.info(
            f'Changed mods to: {client.match.mods.short}'
        )
        client.match.send_referee_message(
            f'Changed mods to: {client.match.mods.short}',
            session.banchobot
        )

    mods_changed = client.match.mods != mods_before

    if mods_changed:
        client.match.unready_players()

    client.match.update()

@register(PacketType.OsuMatchReady)
def ready(client: OsuClient):
    if not client.match:
        return

    client.match.last_activity = time.time()

    if not (slot := client.match.get_slot(client)):
        return

    slot.status = SlotStatus.Ready
    client.match.update()

    if all([slot.status == SlotStatus.Ready for slot in client.match.player_slots]):
        # Notify match referee's that all players are ready
        client.match.send_referee_message(
            'All players are ready.',
            session.banchobot
        )

@register(PacketType.OsuMatchHasBeatmap)
@register(PacketType.OsuMatchNotReady)
def not_ready(client: OsuClient):
    if not client.match:
        return

    client.match.last_activity = time.time()

    if not (slot := client.match.get_slot(client)):
        return

    slot.status = SlotStatus.NotReady
    client.match.update()

@register(PacketType.OsuMatchNoBeatmap)
def no_beatmap(client: OsuClient):
    if not client.match:
        return

    client.match.last_activity = time.time()

    if client.match.beatmap_id <= 0:
        # Beatmap is being selected by the host
        return

    if not (slot := client.match.get_slot(client)):
        return

    slot.status = SlotStatus.NoMap
    client.match.update()

@register(PacketType.OsuMatchLock)
def lock(client: OsuClient, slot_id: int):
    if not client.match:
        return

    if client is not client.match.host:
        return

    client.match.last_activity = time.time()

    if not 0 <= slot_id < config.MULTIPLAYER_MAX_SLOTS:
        return

    slot = client.match.slots[slot_id]

    if slot.player is client:
        # Player can't kick themselves
        return

    if slot.has_player:
        client.match.kick_player(slot.player)

    slot.status = (
        SlotStatus.Open
        if slot.status == SlotStatus.Locked
        else SlotStatus.Locked
    )

    client.match.update()

@register(PacketType.OsuMatchChangeTeam)
def change_team(client: OsuClient):
    if not client.match:
        return

    if not client.match.ffa:
        return

    client.match.last_activity = time.time()

    if not (slot := client.match.get_slot(client)):
        return

    slot.team = {
        SlotTeam.Neutral: SlotTeam.Red,
        SlotTeam.Blue: SlotTeam.Red,
        SlotTeam.Red: SlotTeam.Blue
    }[slot.team]

    client.match.update()
    client.match.send_referee_message(
        f'{client.name} joined team {slot.team.name}.',
        session.banchobot
    )

@register(PacketType.OsuMatchTransferHost)
def transfer_host(client: OsuClient, slot_id: int):
    if not client.match:
        return

    if client is not client.match.host:
        return

    client.match.last_activity = time.time()

    if not 0 <= slot_id < config.MULTIPLAYER_MAX_SLOTS:
        return

    if not (target := client.match.slots[slot_id].player):
        client.match.logger.warning('Host tried to transfer host into an empty slot?')
        return

    if target is client.match.host:
        client.match.host.enqueue_packet(PacketType.BanchoMatchTransferHost)
        return

    client.match.host = target
    client.match.host.enqueue_packet(PacketType.BanchoMatchTransferHost)

    events.create(
        client.match.db_match.id,
        type=EventType.Host,
        data={
            'new': {'id': target.id, 'name': target.name},
            'previous': {'id': client.id, 'name': client.name}
        }
    )

    client.match.logger.info(f'Changed host to: {target.name}')
    client.match.update()

@register(PacketType.OsuMatchChangePassword)
def change_password(client: OsuClient, update: Match):
    if not client.match:
        return

    if client is not client.match.host:
        return

    client.match.password = update.password
    client.match.update()

    client.match.logger.info(
        f'Changed password to: {update.password}'
    )

@register(PacketType.OsuMatchStart)
def match_start(client: OsuClient):
    if not client.match:
        return

    client.match.last_activity = time.time()

    if client is not client.match.host:
        return

    client.match.start()

@register(PacketType.OsuMatchLoadComplete)
def load_complete(client: OsuClient):
    if not client.match:
        return

    if not client.match.in_progress:
        return

    if not (slot := client.match.get_slot(client)):
        return

    slot.loaded = True

    if all(client.match.loaded_players):
        for slot in client.match.slots:
            if not slot.has_map:
                continue

            slot.player.enqueue_packet(PacketType.BanchoMatchAllPlayersLoaded)

        client.match.update()

@register(PacketType.OsuMatchSkipRequest)
def skip(client: OsuClient):
    if not client.match:
        return

    if not client.match.in_progress:
        return

    slot, id = client.match.get_slot_with_id(client)

    if not slot:
        return

    slot.skipped = True

    for p in client.match.players:
        p.enqueue_packet(PacketType.BanchoMatchPlayerSkipped, id)

    for slot in client.match.slots:
        if slot.status == SlotStatus.Playing and not slot.skipped:
            return

    for p in client.match.players:
        p.enqueue_packet(PacketType.BanchoMatchSkip)

@register(PacketType.OsuMatchFailed)
def player_failed(client: OsuClient):
    if not client.match:
        return

    if not client.match.in_progress:
        return

    slot, slot_id = client.match.get_slot_with_id(client)
    assert slot_id is not None

    slot.has_failed = True

    for p in client.match.players:
        p.enqueue_packet(PacketType.BanchoMatchPlayerFailed, slot_id)

@register(PacketType.OsuMatchScoreUpdate)
def score_update(client: OsuClient, scoreframe: ScoreFrame):
    if not client.match:
        return

    slot, id = client.match.get_slot_with_id(client)

    if not slot:
        return

    if not slot.is_playing:
        return

    slot.last_frame = scoreframe
    scoreframe.id = id

    # Append to score queue
    client.match.score_queue.put(scoreframe)
    client.match.last_activity = time.time()

@register(PacketType.OsuMatchComplete)
def match_complete(client: OsuClient):
    if not client.match:
        return

    if not client.match.in_progress:
        return

    client.match.last_activity = time.time()
    client.match.schedule_finish_timeout()

    if not (slot := client.match.get_slot(client)):
        return

    slot.status = SlotStatus.Complete
    client.match.update()

    client.match.send_referee_message(
        f'{client.name} finished playing '
        f'(Score: {slot.last_frame.total_score}, {"FAILED" if slot.has_failed else "PASSED"})',
        session.banchobot
    )

    if any([slot.is_playing for slot in client.match.slots]):
        return

    client.match.finish()

@register(PacketType.OsuTournamentMatchInfo)
def tourney_match_info(client: OsuClient, match_id: int):
    if not client.is_supporter:
        client.logger.warning('Tried to request tourney match info, but was not supporter.')
        return

    if not client.is_tourney_client:
        client.logger.warning('Tried to request tourney match info, but was not in tourney client.')
        return

    client.logger.debug(f'Requesting tourney match info ({match_id})')

    if not session.matches.exists(match_id):
        client.logger.warning('Tried to request tourney match info, but match was not found in active matches.')
        client.enqueue_packet(PacketType.BanchoMatchDisband, match_id)
        return

    match = session.matches[match_id]

    # Clear password for tourney clients
    match_password = copy(match.password)

    if match.password:
        match.password = " "

    client.spectating_match = match
    client.logger.debug(f'Got tournament match info request for "{match.name}".')
    client.enqueue_packet(PacketType.BanchoMatchUpdate, match)

    # Re-apply password
    match.password = match_password

@register(PacketType.OsuTournamentJoinMatchChannel)
def tourney_join_match_channel(client: OsuClient, match_id: int):
    if not client.is_supporter:
        client.logger.warning('Tried to join tourney match channel, but was not supporter.')
        return

    if not client.is_tourney_client:
        client.logger.warning('Tried to join tourney match channel, but was not in tourney client.')
        return

    if not session.matches.exists(match_id):
        client.logger.warning('Tried to join tourney match channel, but match was not found in active matches.')
        return

    match = session.matches[match_id]
    match.chat.add(client)
    client.enqueue_channel(match.chat.bancho_channel, autojoin=True)

@register(PacketType.OsuTournamentLeaveMatchChannel)
def tourney_leave_match_channel(client: OsuClient, match_id: int):
    if not client.is_supporter:
        client.logger.warning('Tried to leave tourney match channel, but was not supporter.')
        return

    if not client.is_tourney_client:
        client.logger.warning('Tried to leave tourney match channel, but was not in tourney client.')
        return

    if not session.matches.exists(match_id):
        client.logger.warning('Tried to leave tourney match channel, but match was not found in active matches.')
        return

    match = session.matches[match_id]
    match.chat.remove(client)
    client.enqueue_channel_revoked(match.chat.display_name)
