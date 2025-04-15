
from __future__ import annotations

from typing import List, NamedTuple, Callable, Tuple, Dict, Any
from pytimeparse.timeparse import timeparse
from dataclasses import dataclass, field
from datetime import timedelta, datetime
from threading import Thread

from .common import officer
from .common.cache import leaderboards
from .common.database.repositories import (
    infringements,
    beatmapsets,
    beatmaps,
    matches,
    clients,
    reports,
    groups,
    events,
    scores,
    stats,
    users
)

from .common.constants import (
    MatchScoringTypes,
    MatchTeamTypes,
    Permissions,
    SlotStatus,
    EventType,
    MatchType,
    SlotTeam,
    GameMode,
    Mods
)

from .objects.channel import Channel, MultiplayerChannel
from .common.objects import bMessage, bMatch, bSlot
from .objects.multiplayer import StartingTimers
from .objects.multiplayer import Match
from .objects.player import Player

import timeago
import config
import random
import string
import time
import app
import os

@dataclass
class Context:
    player: Player
    trigger: str
    target: Channel | Player
    args: List[str]
    set: CommandSet | None = None
    objects: Dict[str, Any] = field(default_factory=dict)

    @property
    def full_trigger(self) -> str:
        return f'{self.set.trigger} {self.trigger}' if self.set else self.trigger

    @property
    def message(self) -> str:
        return f'!{self.full_trigger} {" ".join(self.args)}'
    
    def set_context_object(self, key: str, value: Any) -> None:
        self.objects[key] = value

    def get_context_object(self, key: str) -> Any:
        return self.objects.get(key)

class Command(NamedTuple):
    triggers: List[str]
    callback: Callable
    groups: List[str]
    hidden: bool
    doc: str | None = None
    ignore_conditions: bool = False

class CommandSet:
    def __init__(self, trigger: str, doc: str) -> None:
        self.trigger = trigger
        self.doc = doc

        self.conditions: List[Callable] = []
        self.commands: List[Command] = []

    def register(
        self,
        aliases:
        List[str],
        groups: List[str] = ['Players'],
        hidden: bool = False,
        ignore_conditions: bool = False
    ) -> Callable:
        def wrapper(f: Callable):
            self.commands.append(
                Command(
                    aliases,
                    f,
                    groups,
                    hidden,
                    f.__doc__,
                    ignore_conditions
                )
            )
            return f
        return wrapper

    def condition(self, f: Callable) -> Callable:
        self.conditions.append(f)
        return f

commands: List[Command] = []
sets = [
    mp_commands := CommandSet('mp', 'Multiplayer Commands'),
    system_commands := CommandSet('system', 'System Commands')
]

@system_commands.condition
def is_admin(ctx: Context) -> bool:
    return ctx.player.is_admin

@system_commands.register(['maintenance', 'panic'], ['Admins'])
def maintenance_mode(ctx: Context) -> List[str]:
    """<on/off>"""
    if ctx.args:
        # Change maintenance value based on input
        config.MAINTENANCE = ctx.args[0].lower() == 'on'
    else:
        # Toggle maintenance value
        config.MAINTENANCE = not config.MAINTENANCE

    if config.MAINTENANCE:
        for player in app.session.players:
            if player.is_admin:
                continue

            player.close_connection()

    return [
        f'Maintenance mode is now {"enabled" if config.MAINTENANCE else "disabled"}.'
    ]

@system_commands.register(['setenv', 'setcfg'], ['Admins'])
def set_config_value(ctx: Context) -> List[str]:
    """<env> <value> - Update a config value"""
    if len(ctx.args) < 2:
        return [f'Invalid syntax: !{system_commands.trigger} {ctx.trigger} <env> <value>']

    env_name = ctx.args[0]
    value = ' '.join(ctx.args[1:])

    config.dotenv.set_key('.env', env_name, value)
    setattr(config, env_name, value)

    if env_name.startswith('MENUICON'):
        # Enqueue menu icon to all players
        for player in app.session.players:
            player.send_packet(
                player.packets.MENU_ICON,
                config.MENUICON_IMAGE,
                config.MENUICON_URL
            )

    return ['Config was updated.']

@system_commands.register(['getenv', 'getcfg', 'env', 'config', 'cfg'], ['Admins'])
def get_config_value(ctx: Context) -> List[str]:
    """<env> - Get a config value"""
    if len(ctx.args) < 1:
        return [f'Invalid syntax: !{system_commands.trigger} {ctx.trigger} <env>']

    return [getattr(config, ctx.args[0])]

@system_commands.register(['reloadcfg', 'reloadenv'], ['Admins'])
def reload_config(ctx: Context) -> List[str]:
    """- Reload the config"""

    config.dotenv.load_dotenv(override=True)

    for key in dir(config):
        if not key.isupper():
            continue

        if key not in os.environ:
            continue

        setattr(config, key, os.environ[key])

    return ['Config was reloaded.']

@system_commands.register(['exec', 'python'], ['Admins'])
def execute_console(ctx: Context):
    """<input> - Execute any python code"""
    if not ctx.args:
        return [f'Invalid syntax: !{system_commands.trigger} {ctx.trigger} <input>']

    input = ' '.join(ctx.args)
    return [str(eval(input))]

def resolve_match(ctx: Context) -> Match | None:
    if type(ctx.target) != MultiplayerChannel:
        # User is not inside a multiplayer channel
        return None

    return ctx.target.match

@mp_commands.condition
def inside_match(ctx: Context) -> bool:
    if not (match := resolve_match(ctx)):
        return False

    ctx.set_context_object('match', match)
    return True

@mp_commands.condition
def is_host(ctx: Context) -> bool:
    non_host_commands = ('link', 'url', 'settings')

    if ctx.trigger in non_host_commands:
        return True
    
    match = ctx.get_context_object('match')

    if not match:
        return False

    return (ctx.player is match.host) or \
           (ctx.player.id in match.referee_players) or \
           (ctx.player.is_admin)

@mp_commands.condition
def inside_chat(ctx: Context) -> bool:
    return ctx.target is ctx.get_context_object('match').chat

@mp_commands.register(['help', 'h'], hidden=True)
def mp_help(ctx: Context):
    """- Shows this message"""
    response = []

    for command in mp_commands.commands:
        has_permissions = any(
            group in command.groups
            for group in ctx.player.groups
        )

        if not has_permissions:
            continue

        if not command.doc:
            continue

        response.append(f'!{mp_commands.trigger.upper()} {command.triggers[0].upper()} {command.doc}')

    return response

@mp_commands.register(['create', 'make', 'makeprivate', 'createprivate'], ignore_conditions=True, groups=['Admins', 'Tournament Manager Team', 'Global Moderator Team'])
def create_persistant_match(ctx: Context):
    """<name> - Create a new persistant match"""
    if len(ctx.args) < 1:
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <name>']

    if len(ctx.player.referee_matches) > 3:
        return ['You have reached the maximum amount of persistant matches.']

    if ctx.player.is_tourney_client:
        return ['You cannot create a persistant match inside of a tourney client.']

    if ctx.player.match:
        return ['Please leave your current match first.']

    is_private = ctx.trigger in ('makeprivate', 'createprivate')
    password = ''.join(random.choice(string.ascii_uppercase) for _ in range(15))

    match = Match(
        id=-1,
        name=" ".join(ctx.args[0:])[:50],
        password=password if is_private else "",
        host=ctx.player,
        mode=ctx.player.status.mode,
        persistant=True
    )

    if not app.session.matches.append(match):
        ctx.player.logger.warning('Failed to append match to collection')
        ctx.player.enqueue_matchjoin_fail()
        return ['Could not create match.']

    ctx.player.referee_matches.add(match.id)
    match.referee_players.append(ctx.player.id)
    match.chat = MultiplayerChannel(match)
    app.session.channels.add(match.chat)

    match.db_match = matches.create(
        match.name,
        match.id,
        match.host.id
    )

    app.session.logger.info(
        f'Created persistant match: "{match.name}"'
    )

    channel_object = match.chat.bancho_channel
    channel_object.name = match.chat.name

    ctx.player.enqueue_channel(channel_object, autojoin=True)
    match.chat.add(ctx.player)

    slot = match.slots[0]
    slot.status = SlotStatus.NotReady
    slot.player = ctx.player

    events.create(
        match.db_match.id,
        type=EventType.Join,
        data={
            'user_id': ctx.player.id,
            'name': ctx.player.name
        }
    )

    match.logger.info(f'{ctx.player.name} joined')
    match.update()

    ctx.player.match = match
    ctx.player.enqueue_matchjoin_success(match.bancho_match)

    match.chat.send_message(
        app.session.banchobot,
        f"Match history available [http://osu.{config.DOMAIN_NAME}/mp/{match.db_match.id} here].",
        ignore_privileges=True
    )

    # Force-revoke #multiplayer
    ctx.player.revoke_channel('#multiplayer')

    return ['Match created.']

@mp_commands.register(['start', 'st'])
def mp_start(ctx: Context):
    """<force/seconds/cancel> - Start the match, with any players that are ready"""
    if len(ctx.args) > 1:
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <force/seconds/cancel>']

    match: Match = ctx.get_context_object('match')

    if match.in_progress:
        return ['This match is already running.']

    if not ctx.args:
        # Check if match is starting
        if match.starting:
            time_remaining = round(match.starting.time - time.time())
            return [f'Match starting in {time_remaining} seconds.']

        if not match.player_slots:
            return ['There are no players inside this match.']

        # Check if players are ready
        if any([s.status == SlotStatus.NotReady for s in match.slots]):
            return [f'Not all players are ready ("!{mp_commands.trigger}" {ctx.trigger} force" to start anyways)']

        match.start()
        return ['Match was started. Good luck!']

    if ctx.args[0].isdecimal():
        # Host wants to start a timer
        if match.starting:
            # Timer is already running
            time_remaining = round(match.starting.time - time.time())
            return [f'Match starting in {time_remaining} seconds.']

        duration = int(ctx.args[0])

        if duration < 0:
            return ['no.']

        if duration > 300:
            return ['Please lower your duration!']

        match.starting = StartingTimers(
            time.time() + duration,
            timer := Thread(
                target=match.execute_timer,
                daemon=True
            )
        )

        timer.start()

        return [f'Match starting in {duration} {"seconds" if duration != 1 else "second"}.']

    elif ctx.args[0] in ('cancel', 'c'):
        # Host wants to cancel the timer
        if not match.starting:
            return ['Match timer is not active!']

        # The timer thread will check if 'starting' is None
        match.starting = None
        return ['Match timer was cancelled.']

    elif ctx.args[0] in ('force', 'f'):
        match.start()
        return ['Match was started. Good luck!']

    return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <force/seconds/cancel>']

@mp_commands.register(['close', 'terminate', 'disband'])
def mp_close(ctx: Context):
    """- Close a match and kick all players"""
    match: Match = ctx.get_context_object('match')
    match.logger.info('Match was closed.')
    match.close()
    return ['Match was closed.']

@mp_commands.register(['abort'])
def mp_abort(ctx: Context):
    """- Abort the current match"""
    match: Match = ctx.get_context_object('match')

    if not match.in_progress:
        return ["Nothing to abort."]

    match.abort()
    match.logger.info('Match was aborted.')
    return ['Match aborted.']

@mp_commands.register(['map', 'setmap', 'beatmap'])
def mp_map(ctx: Context):
    """<beatmap_id> - Select a new beatmap by it's id"""
    if len(ctx.args) != 1 or not ctx.args[0].isdecimal():
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <beatmap_id>']

    match: Match = ctx.get_context_object('match')
    beatmap_id = int(ctx.args[0])

    if beatmap_id == match.beatmap_id:
        return ['That map was already selected.']

    if not (map := beatmaps.fetch_by_id(beatmap_id)):
        return ['Could not find that beatmap.']

    match.beatmap_id = map.id
    match.beatmap_hash = map.md5
    match.beatmap_name = map.full_name
    match.mode = GameMode(map.mode)
    match.update()

    match.logger.info(f'Selected: {map.full_name}')
    return [f'Selected: {map.link}']

@mp_commands.register(['mods', 'setmods'])
def mp_mods(ctx: Context):
    """<mods> - Set the current match's mods (e.g. HDHR)"""
    if len(ctx.args) < 1:
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <mods>']

    # TODO: Filter out invalid mods
    mods, freemod = parse_mods_from_args(ctx.args)

    if mods is None:
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <mods>']

    if mods.value >= 4294967295:
        # This would hit the integer limit
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <mods>']

    match: Match = ctx.get_context_object('match')

    if mods == match.mods and freemod == match.freemod:
        return [f'Mods are already set to {match.mods.short}{"FM" if freemod else ""}.']

    match.freemod = freemod

    if match.freemod:
        # Set match mods
        match.mods = mods & ~Mods.FreeModAllowed

        # Set host mods
        match.host_slot.mods = mods & ~Mods.SpeedMods
    else:
        match.mods = mods

    match.logger.info(f'Updated match mods to {match.mods.short}.')
    match.update()
    return [f'Updated match mods to {match.mods.short}{"FM" if freemod else ""}.']

def parse_mods_from_args(args: List[str]) -> Tuple[Mods, bool]:
    try:
        freemod = any(arg.lower() in ('freemod', 'fm') for arg in args)

        if args[0].isdecimal():
            # Parse mods as an integer
            return Mods(int(args[0])), freemod

        # Parse mods from their short forms, e.g. HDHR or HDDT
        mods_string = "".join(args[0:]).replace(',', '').replace("freemod", "")
        freemod = "fm" in mods_string.lower() or freemod

        if len(args[0]) % 2 != 0:
            # Mod string must be a multiple of 2
            return

        return Mods.from_string(mods_string), freemod
    except (ValueError, TypeError):
        pass

@mp_commands.register(['freemod', 'fm', 'fmod'])
def mp_freemod(ctx: Context):
    """<on/off> - Enable or disable freemod status."""
    valid_args = (
        "on", "true", "yes", "1",
        "off", "false", "no", "0",
    )

    if len(ctx.args) != 1 or ctx.args[0] not in valid_args:
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <on/off>']

    match: Match = ctx.get_context_object('match')
    freemod = ctx.args[0] in ('on', 'true', 'yes', '1')

    if match.freemod == freemod:
        return [f'Freemod is already {"enabled" if freemod else "disabled"}.']

    match.unready_players()
    match.freemod = freemod
    match.logger.info(f'Freemod: {freemod}')

    if freemod:
        for slot in match.slots:
            if slot.status.value & SlotStatus.HasPlayer.value:
                # Set current mods to every player inside the match, if they are not speed mods
                slot.mods = match.mods & ~Mods.SpeedMods

                # TODO: Fix for older clients without freemod support
                # slot.mods = []

            # The speedmods are kept in the match mods
            match.mods = match.mods & ~Mods.FreeModAllowed
    else:
        # Keep mods from host, if the host exists
        host_mods = match.host_slot.mods if match.host_slot else Mods.NoMod
        match.mods |= host_mods

        # Reset any mod from players
        for slot in match.slots:
            slot.mods = Mods.NoMod

    match.update()
    return [f'Freemod is now {"enabled" if freemod else "disabled"}.']

@mp_commands.register(['host', 'sethost'])
def mp_host(ctx: Context):
    """<name> - Set the host for this match"""
    if len(ctx.args) <= 0:
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <name>']

    match: Match = ctx.get_context_object('match')
    name = ' '.join(ctx.args[0:])

    if not (target := match.get_player(name)):
        return ['Could not find this player.']

    if target is match.host:
        return ['You are already the host.']

    events.create(
        match.db_match.id,
        type=EventType.Host,
        data={
            'previous': {'id': target.id, 'name': target.name},
            'new': {'id': match.host.id, 'name': match.host.name}
        }
    )

    match.host = target
    match.host.enqueue_match_transferhost()
    match.logger.info(f'Changed host to: {target.name}')
    match.update()

    return [f'{target.name} is now host of this match.']

@mp_commands.register(['clearhost', 'removehost'])
def mp_clearhost(ctx: Context):
    """- Clear the current host"""
    match: Match = ctx.get_context_object('match')

    if match.host is None:
        return ['There is no host to clear.']

    if ctx.player.id not in match.referee_players:
        return ['You are not a referee.']

    match.host = None
    match.update()
    return ['Host was cleared.']

bot_invites = [
    "Uhh... sorry, no time to play. (°_o)",
    "I'm too busy!",
    "nope.",
    "idk how to play this game... ¯\(°_o)/¯"
]

@mp_commands.register(['invite', 'inv'])
def mp_invite(ctx: Context):
    """<name> - Invite a player to this match"""
    if len(ctx.args) <= 0:
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <name>']

    match: Match = ctx.get_context_object('match')
    name = ' '.join(ctx.args[0:])

    if name == app.session.banchobot.name:
        return [bot_invites[random.randrange(0, len(bot_invites))]]

    if not (target := app.session.players.by_name(name)):
        return [f'Could not find the player "{name}".']

    if target is ctx.player:
        return ['You are already here.']

    if target.match is match:
        return ['This player is already here.']

    target.enqueue_invite(
        bMessage(
            ctx.player.name,
            f'Come join my multiplayer match: {match.embed}',
            ctx.player.name,
            ctx.player.id
        )
    )

    return [f'Invited {target.name} to this match.']

@mp_commands.register(['force', 'forceinvite'], ['Admins', 'Tournament Manager Team'])
def mp_force_invite(ctx: Context):
    """<name> - Force a player to join this match"""
    if len(ctx.args) <= 0:
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <name>']

    match: Match = ctx.get_context_object('match')
    name = ' '.join(ctx.args[0:])

    if not ctx.player.is_admin and not match.persistent:
        return ['You are not allowed to force invite players.']

    if not (target := app.session.players.by_name(name)):
        return [f'Could not find the player "{name}".']

    if target.match is match:
        return [f'{target.name} is already in this match.']

    if target.match is not None:
        target.match.kick_player(target)

    if (slot_id := match.get_free()) is None:
        return ['This match is full.']

    # Join the chat
    target.enqueue_channel(match.chat.bancho_channel, autojoin=True)
    match.chat.add(target)

    slot = match.slots[slot_id]

    if match.team_type in (MatchTeamTypes.TeamVs, MatchTeamTypes.TagTeamVs):
        slot.team = SlotTeam.Red

    slot.status = SlotStatus.NotReady
    slot.player = target

    target.match = match
    target.enqueue_matchjoin_success(match.bancho_match)

    match.logger.info(f'{target.name} joined')
    match.update()

    return ['Welcome.']

@mp_commands.register(['lock'])
def mp_lock(ctx: Context):
    """- Lock all unsued slots in the match."""
    match: Match = ctx.get_context_object('match')

    for slot in match.slots:
        if slot.has_player:
            match.kick_player(slot.player)

        if slot.status == SlotStatus.Open:
            slot.status = SlotStatus.Locked

    match.update()
    return ['Locked all unused slots.']

@mp_commands.register(['unlock'])
def mp_unlock(ctx: Context):
    """- Unlock all locked slots in the match."""
    match: Match = ctx.get_context_object('match')

    for slot in match.slots:
        if slot.status == SlotStatus.Locked:
            slot.status = SlotStatus.Open

    match.update()
    return ['Unlocked all locked slots.']

@mp_commands.register(['kick', 'remove'])
def mp_kick(ctx: Context):
    """<name> - Kick a player from the match"""
    if len(ctx.args) <= 0:
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <name>']

    match: Match = ctx.get_context_object('match')
    name = ' '.join(ctx.args[0:]).strip()

    if name == app.session.banchobot.name:
        return ["no."]

    if name == ctx.player.name:
        return ["no."]

    for player in match.players:
        if player.name != name:
            continue

        match.kick_player(player)

        if all(slot.empty for slot in match.slots):
            match.close()
            match.logger.info('Match was disbanded.')

        return ["Player was kicked from the match."]

    return [f'Could not find the player "{name}".']

@mp_commands.register(['ban', 'restrict'])
def mp_ban(ctx: Context):
    """<name> - Ban a player from the match"""
    if len(ctx.args) <= 0:
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <name>']

    match: Match = ctx.get_context_object('match')
    name = ' '.join(ctx.args[0:]).strip()

    if name == app.session.banchobot.name:
        return ["no."]

    if name == ctx.player.name:
        return ["no."]

    if not (player := app.session.players.by_name(name)):
        return [f'Could not find the player "{name}".']

    match.ban_player(player)

    if all(slot.empty for slot in match.slots):
        match.close()
        match.logger.info('Match was disbanded.')

    return ["Player was banned from the match."]

@mp_commands.register(['unban', 'unrestrict'])
def mp_unban(ctx: Context):
    """<name> - Unban a player from the match"""
    if len(ctx.args) <= 0:
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <name>']

    match: Match = ctx.get_context_object('match')
    name = ' '.join(ctx.args[0:]).strip()

    if not (player := app.session.players.by_name(name)):
        return [f'Could not find the player "{name}".']

    if player.id not in match.banned_players:
        return ['Player was not banned from the match.']

    match.unban_player(player)

    return ["Player was unbanned from the match."]

@mp_commands.register(['name', 'setname'])
def mp_name(ctx: Context):
    """<name> - Change the match name"""
    if len(ctx.args) <= 0:
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <name>']

    match: Match = ctx.get_context_object('match')
    name = ' '.join(ctx.args[0:]).strip()

    match.name = name
    match.update()

    matches.update(
        match.db_match.id,
        {"name": name}
    )

@mp_commands.register(['set'])
def mp_set(ctx: Context):
    """<teammode> (<scoremode>) (<size>)"""
    if len(ctx.args) <= 0:
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <teammode> (<scoremode>) (<size>)']

    try:
        match: Match = ctx.get_context_object('match')
        match.team_type = MatchTeamTypes(int(ctx.args[0]))

        if len(ctx.args) > 1:
            match.scoring_type = MatchScoringTypes(int(ctx.args[1]))

        if len(ctx.args) > 2:
            size = max(1, min(int(ctx.args[2]), config.MULTIPLAYER_MAX_SLOTS))

            for slot in match.slots[size:]:
                if slot.has_player:
                    match.kick_player(slot.player)

                slot.reset(SlotStatus.Locked)

            for slot in match.slots[0:size]:
                if slot.has_player:
                    continue

                slot.reset()

            if all(slot.empty for slot in match.slots) and not match.persistent:
                match.close()
                return ["Match was disbanded."]

        match.update()
    except ValueError:
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <teammode> (<scoremode>) (<size>)']

    slot_size = len([slot for slot in match.slots if not slot.locked])

    return [f"Settings changed to {match.team_type.name}, {match.scoring_type.name}, {slot_size} slots."]

@mp_commands.register(['size'])
def mp_size(ctx: Context):
    """<size> - Set the amount of available slots (1-8)"""
    if len(ctx.args) <= 0:
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <size>']

    match: Match = ctx.get_context_object('match')
    size = max(1, min(int(ctx.args[0]), config.MULTIPLAYER_MAX_SLOTS))

    for slot in match.slots[size:]:
        if slot.has_player:
            match.kick_player(slot.player)

        slot.reset(SlotStatus.Locked)

    for slot in match.slots[0:size]:
        if slot.has_player:
            continue

        slot.reset()

    if all(slot.empty for slot in match.slots) and not match.persistent:
        match.close()
        return ["Match was disbanded."]

    match.update()
    return [f"Changed slot size to {size}."]

@mp_commands.register(['move'])
def mp_move(ctx: Context):
    """<name> <slot> - Move a player to a slot"""
    if len(ctx.args) <= 1:
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <name> <slot>']

    match: Match = ctx.get_context_object('match')
    name = ctx.args[0]
    slot_id = max(1, min(int(ctx.args[1]), config.MULTIPLAYER_MAX_SLOTS))

    if not (player := match.get_player(name)):
        return [f'Could not find player {name}.']

    old_slot = match.get_slot(player)

    # Check if slot is already used
    if (slot := match.slots[slot_id-1]).has_player:
        return [f'This slot is already in use by {slot.player.name}.']

    slot.copy_from(old_slot)
    old_slot.reset()

    match.update()
    return [f'Moved {player.name} into slot {slot_id}.']

@mp_commands.register(['settings'], hidden=True)
def mp_settings(ctx: Context):
    """- View the current match settings"""
    match: Match = ctx.get_context_object('match')
    beatmap_link = (
        f'[http://osu.{config.DOMAIN_NAME}/b/{match.beatmap_id} {match.beatmap_name}]'
        if match.beatmap_id > 0 else match.beatmap_name
    )

    return [
        f"Room Name: {match.name} ([http://osu.{config.DOMAIN_NAME}/mp/{match.db_match.id} View History])",
        f"Beatmap: {beatmap_link}",
        f"Active Mods: +{match.mods.short}",
        f"Team Mode: {match.team_type.name}",
        f"Win Condition: {match.scoring_type.name}",
        f"Players: {len(match.players)}",
       *[
            f"{match.slots.index(slot) + 1} ({slot.status.name}) - "
            f"[http://osu.{config.DOMAIN_NAME}/u/{slot.player.id} {slot.player.name}]"
            f"{f' +{slot.mods.short}' if slot.mods > 0 else ' '} [{f'Host' if match.host == slot.player else ''}]"
            for slot in match.slots
            if slot.has_player
        ]
    ]

@mp_commands.register(['team', 'setteam'])
def mp_team(ctx: Context):
    """<name> <color> - Set a players team color"""
    if len(ctx.args) <= 1:
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <name> <color>']

    match: Match = ctx.get_context_object('match')
    name = ctx.args[0]
    team = ctx.args[1].capitalize()

    if team not in ("Red", "Blue", "Neutral"):
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <name> <red/blue>']

    if team == "Neutral" and match.ffa:
        match.team_type = MatchTeamTypes.HeadToHead

    elif team != "Neutral" and not match.ffa:
        match.team_type = MatchTeamTypes.TeamVs

    if not (player := match.get_player(name)):
        return [f'Could not find player "{name}"']

    slot = match.get_slot(player)
    slot.team = SlotTeam[team]

    match.update()
    return [f"Moved {player.name} to team {team}."]

@mp_commands.register(['password', 'setpassword', 'pass'])
def mp_password(ctx: Context):
    """(<password>) - (Re)set the match password"""
    match: Match = ctx.get_context_object('match')

    if not ctx.args:
        match.password = ""
        match.update()
        return ["Match password was reset."]

    match.password = " ".join(ctx.args[0:])
    match.update()
    return ["Match password was set."]

@mp_commands.register(['link', 'url'])
def mp_link(ctx: Context):
    """- Get the link to the current match"""
    match: Match = ctx.get_context_object('match')

    if not match:
        return ["You are not inside a match."]

    return [
        f'Match history available '
        f'[http://osu.{config.DOMAIN_NAME}/mp/{match.db_match.id} here].'
    ]

@mp_commands.register(['listrefs', 'listreferees'])
def mp_listrefs(ctx: Context):
    """- List all referees in the current match"""
    match: Match = ctx.get_context_object('match')

    if not match:
        return ["You are not inside a match."]

    referees_targets = {
        player_id: app.session.players.by_id(player_id)
        for player_id in match.referee_players
    }

    referees = [
        f"[http://osu.{config.DOMAIN_NAME}/u/{id} {player.name if player else 'Unknown'}]"
        for id, player in referees_targets.items()
    ]

    for player in referees_targets.values():
        if player is None:
            continue

        if match in player.referee_matches:
            continue

        # Ensure the match is added to the players referee matches
        player.referee_matches.add(match)

    return [
        f"Match referees: {', '.join(referees)}"
        if referees else "There are no referees in this match."
    ]

@mp_commands.register(['addref', 'addreferee'], ['Admins', 'Tournament Manager Team', 'Global Moderator Team'])
def mp_addref(ctx: Context):
    """<username> - Add a referee to this match"""
    match: Match = ctx.get_context_object('match')

    if not match:
        return ["You are not inside a match."]

    if not match.persistent:
        return ["This match is not persistent."]

    if match.chat.owner != ctx.player.name:
        return ["You are not the owner of this match."]

    if len(ctx.args) < 1:
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <username>']

    name = ' '.join(ctx.args[0:])

    if not (target := app.session.players.by_name(name)):
        return [f'Could not find player "{name}".']

    if target.id in match.referee_players:
        return [f'{target.name} is already a referee.']

    if target.id == ctx.player.id:
        return ["You cannot add yourself as a referee."]

    if target.match:
        return [f'{target.name} is already in a match.']

    match.referee_players.append(target.id)
    target.referee_matches.add(match)

    channel_object = match.chat.bancho_channel
    channel_object.name = match.chat.name

    target.enqueue_channel(channel_object, autojoin=True)
    match.chat.add(target)

    return [f'Added "{target.name}" as a match referee.']

@mp_commands.register(['removeref', 'remref', 'removereferee'], ['Admins', 'Tournament Manager Team', 'Global Moderator Team'])
def mp_removeref(ctx: Context):
    """<username> - Remove a referee from this match"""
    match: Match = ctx.get_context_object('match')

    if not match:
        return ["You are not inside a match."]

    if not match.persistent:
        return ["This match is not persistent."]

    if match.chat.owner != ctx.player.name:
        return ["You are not the owner of this match."]

    if len(ctx.args) < 1:
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <username>']

    name = ' '.join(ctx.args[0:])

    if not (target := app.session.players.by_name(name)):
        return [f'Could not find player "{name}".']

    if target.id not in match.referee_players:
        return [f'{target.name} is not a referee.']

    if target.id == ctx.player.id:
        return ["You cannot remove yourself as a referee."]

    match.chat.remove(target)
    match.referee_players.remove(target.id)
    target.referee_matches.remove(match)
    target.revoke_channel(match.chat.bancho_channel.name)

    return [f'Removed "{target.name}" from match referee status.']

def command(
    aliases: List[str],
    groups: List[str] = ['Players'],
    hidden: bool = True,
) -> Callable:
    def wrapper(f: Callable) -> Callable:
        commands.append(
            Command(
                aliases,
                f,
                groups,
                hidden,
                f.__doc__
            ),
        )
        return f
    return wrapper

@command(['help', 'h', ''])
def help(ctx: Context) -> List | None:
    """- Shows this message"""
    response = []

    # Standard commands
    response.append('Standard Commands:')
    for command in commands:
        has_permissions = any(
            group in command.groups
            for group in ctx.player.groups
        )

        if not has_permissions:
            continue

        response.append(
            f'!{command.triggers[0].upper()} {command.doc}'
        )

    # Command sets
    for set in sets:
        if not set.commands:
            # Set has no commands
            continue

        for condition in set.conditions:
            if not condition(ctx):
                break
        else:
            response.append(f'{set.doc} (!{set.trigger}):')

            for command in set.commands:
                has_permissions = any(
                    group in command.groups
                    for group in ctx.player.groups
                )

                if not has_permissions:
                    continue

                if not command.doc:
                    continue

                response.append(
                    f'!{set.trigger.upper()} {command.triggers[0].upper()} {command.doc}'
                )

    return response

@command(['roll'], hidden=False)
def roll(ctx: Context) -> List | None:
    """<number> - Roll a dice and get random result from 1 to <number> (default 100)"""
    max_roll = 100

    if ctx.args and ctx.args[0].isdecimal():
        max_roll = int(ctx.args[0])

        if max_roll <= 0:
            return ['no.']

        # User set a custom roll number
        max_roll = min(max_roll, 0x7FFF)

    return [f'{ctx.player.name} rolls {random.randrange(0, max_roll+1)}!']

@command(['report'])
def report(ctx: Context) -> List | None:
    """<username> <reason>"""
    if len(ctx.args) < 1:
        return [f'Invalid syntax: !{ctx.trigger} <username> (<reason>)']

    username = ctx.args[0]
    reason = ' '.join(ctx.args[1:])[:255]

    if not (target := users.fetch_by_name(username)):
        return [f'Could not find player "{username}".']

    if target.id == ctx.player.id:
        return ['You cannot report yourself.']

    if target.name == app.session.banchobot.name:
        return ['no.']

    if r := reports.fetch_by_sender_to_target(ctx.player.id, target.id):
        seconds_since_last_report = (
            datetime.now().timestamp() - r.time.timestamp()
        )

        if seconds_since_last_report <= 86400:
            return [
                'You have already reported that user. '
                'Please wait until you report them again!'
            ]

    if channel := app.session.channels.by_name('#admin'):
        # Send message to admin chat
        channel.send_message(
            app.session.banchobot,
            f'[{ctx.target.name}] {ctx.player.link} reported {target.link} for: "{reason}".'
        )

    # Create record in database
    reports.create(
        target.id,
        ctx.player.id,
        reason
    )

    return ['Chat moderators have been alerted. Thanks for your help.']

@command(['search'], ['Supporters'], hidden=False)
def search(ctx: Context):
    """<query> - Search a beatmap"""
    query = ' '.join(ctx.args[0:])

    if len(query) <= 2:
        return ['Query too short']

    if not (result := beatmapsets.search_one(query)):
        return ['No matches found']

    status = {
        -2: 'Graveyarded',
        -1: 'WIP',
         0: 'Pending',
         1: 'Ranked',
         2: 'Approved',
         3: 'Qualified',
         4: 'Loved'
    }[result.status]

    return [f'{result.link} [{status}]']

@command(['where', 'location'], hidden=False)
def where(ctx: Context):
    """<name> - Get a player's current location"""
    if len(ctx.args) < 1:
        return [f'Invalid syntax: !{ctx.trigger} <username>']

    name = ' '.join(ctx.args[0:])

    if not (target := app.session.players.by_name(name)):
        return ['Player is not online']

    if not target.client.ip:
        return ['The players location data could not be resolved']

    city_string = f"({target.client.ip.city})" if target.client.display_city else ""
    location_string = target.client.ip.country_name

    return [f'{target.name} is in {location_string} {city_string}']

@command(['stats'], hidden=False)
def get_stats(ctx: Context):
    """<username> - Get the stats of a player"""
    if len(ctx.args) < 1:
        return [f'Invalid syntax: !{ctx.trigger} <username>']

    name = ' '.join(ctx.args[0:])

    if not (target := app.session.players.by_name(name)):
        return ['Player is not online']

    global_rank = leaderboards.global_rank(target.id, target.status.mode.value)
    score_rank = leaderboards.score_rank(target.id, target.status.mode.value)

    return [
        f'Stats for [http://osu.{config.DOMAIN_NAME}/u/{target.id} {target.name}] is {target.status.action.name}:',
        f'  Score:    {format(target.current_stats.rscore, ",d")} (#{score_rank})',
        f'  Plays:    {target.current_stats.playcount} (lv{target.level})',
        f'  Accuracy: {round(target.current_stats.acc * 100, 2)}%',
        f'  PP:       {round(target.current_stats.pp, 2)}pp (#{global_rank})'
    ]

@command(['recent', 'r', 'last'], hidden=False)
def recent(ctx: Context):
    """- Get information about your last score"""
    target_player = ctx.player

    if ctx.args:
        name = ' '.join(ctx.args[0:])

        if not (target_player := app.session.players.by_name(name)):
            return ['Player is not online']

    with app.session.database.managed_session() as session:
        recent_scores = scores.fetch_recent_all(
            user_id=target_player.id,
            limit=1,
            session=session
        )

        if not recent_scores:
            return ['No recent scores found.']

        score = recent_scores[0]
        passed = score.failtime is None

        response = [
            f"[{GameMode(score.mode).formatted}] "
            f"{score.beatmap.link} "
            f"{score.max_combo}/{score.beatmap.max_combo} "
            f"{score.acc * 100:.2f}%"
            f'{(f" +{Mods(score.mods).short}" if score.mods else "")}'
        ]

        if passed:
            rank = scores.fetch_score_index_by_id(
                score.id,
                score.beatmap_id,
                score.mode,
                score.mods,
                session=session
            ) or 'NA'
            response.append(f"{score.grade} ({score.pp:.2f}pp #{rank})")

        else:
            completion = max(1, score.failtime) / (max(1, score.beatmap.total_length) * 1000)
            response.append(f"{score.grade} ({completion * 100:.2f}% complete)")

        return [" | ".join(response)]

@command(['client', 'version'], hidden=False)
def get_client_version(ctx: Context):
    """<username> - Get the version of the client that a player is currently using"""
    target = ctx.player

    if len(ctx.args) > 0:
        # Select a different player
        name = ' '.join(ctx.args[0:])

        if not (target := app.session.players.by_name(name)):
            return ['Player is not online']

    return [f"{target.name} is playing on {target.client.version.string}"]

@command(['monitor'], ['Admins'])
def monitor(ctx: Context) -> List | None:
    """<name> - Monitor a player"""

    if len(ctx.args) < 1:
        return [f'Invalid syntax: !{ctx.trigger} <name>']

    name = ' '.join(ctx.args[0:])

    if not (player := app.session.players.by_name(name)):
        return ['Player is not online']

    player.enqueue_monitor()

    return ['Player has been monitored']

@command(['alert', 'announce', 'broadcast'], ['Admins', 'Developers'])
def alert(ctx: Context) -> List | None:
    """<message> - Send a message to all players"""

    if not ctx.args:
        return [f'Invalid syntax: !{ctx.trigger} <message>']

    app.session.players.announce(' '.join(ctx.args))

    return [f'Alert was sent to {len(app.session.players)} players.']

@command(['alertuser'], ['Admins', 'Developers'])
def alertuser(ctx: Context) -> List | None:
    """<username> <message> - Send a notification to a player"""

    if len(ctx.args) < 2:
        return [f'Invalid syntax: !{ctx.trigger} <username> <message>']

    username = ctx.args[0]

    if not (player := app.session.players.by_name(username)):
        return [f'Could not find player "{username}".']

    player.enqueue_announcement(' '.join(ctx.args[1:]))

    return [f'Alert was sent to {player.name}.']

@command(['silence', 'mute'], ['Admins', 'Developers', 'Global Moderator Team'], hidden=False)
def silence(ctx: Context) -> List | None:
    """<username> <duration> (<reason>)"""

    if len(ctx.args) < 2:
        return [f'Invalid syntax: !{ctx.trigger} <username> <duration> (<reason>)']

    name = ctx.args[0]
    duration = timeparse(ctx.args[1])
    reason = ' '.join(ctx.args[2:])

    if (player := app.session.players.by_name(name)):
        player.silence(duration, reason)
        silence_end = player.object.silence_end
    else:
        if not (player := users.fetch_by_name(name)):
            return [f'Player "{name}" was not found.']

        if player.silence_end:
            player.silence_end += timedelta(seconds=duration)
        else:
            player.silence_end = datetime.now() + timedelta(seconds=duration)

        users.update(
            player.id,
            {'silence_end': player.silence_end}
        )

        silence_end = player.silence_end

        # Add entry inside infringements table
        infringements.create(
            player.id,
            action=1,
            length=(datetime.now() + timedelta(seconds=duration)),
            description=reason
        )

    if not silence_end:
        return [f'Failed to silence {player.name}.']

    time_string = timeago.format(silence_end)
    time_string = time_string.replace('in ', '')

    return [f'{player.name} was silenced for {time_string}']

@command(['unsilence', 'unmute'], ['Admins', 'Developers', 'Global Moderator Team'], hidden=False)
def unsilence(ctx: Context):
    """- <username>"""

    if len(ctx.args) < 1:
        return [f'Invalid syntax: !{ctx.trigger} <name>']

    name = ctx.args[0]

    if (player := app.session.players.by_name(name)):
        player.unsilence()
        return [f'{player.name} was unsilenced.']

    if not (player := users.fetch_by_name(name)):
        return [f'Player "{name}" was not found.']

    users.update(player.id, {'silence_end': None})

    # Delete infringements from website
    inf = infringements.fetch_recent_by_action(player.id, action=1)
    if inf: infringements.delete_by_id(inf.id)

    return [f'{player.name} was unsilenced.']

@command(['restrict', 'ban'], ['Admins', 'Developers', 'Global Moderator Team'], hidden=False)
def restrict(ctx: Context) -> List | None:
    """ <name> <length/permanent> (<reason>)"""

    if len(ctx.args) < 2:
        return [f'Invalid syntax: !{ctx.trigger} <name> <length/permanent> (<reason>)']

    username = ctx.args[0]
    length   = ctx.args[1]
    reason   = ' '.join(ctx.args[2:])

    if not length.startswith('perma'):
        until = datetime.now() + timedelta(seconds=timeparse(length))
    else:
        until = None

    if not (player := app.session.players.by_name(username)):
        # Player is not online, or was not found
        player = users.fetch_by_name(username)

        if not player:
            return [f'Player "{username}" was not found']

        player.restricted = True

        # Update user
        users.update(player.id, {'restricted': True})

        leaderboards.remove(
            player.id,
            player.country
        )

        scores.hide_all(player.id)
        stats.update_all(player.id, {'rank': 0})

        groups.delete_entry(player.id, 999)
        groups.delete_entry(player.id, 1000)

        # Update hardware
        clients.update_all(player.id, {'banned': True})

        # Add entry inside infringements table
        infringements.create(
            player.id,
            action=0,
            length=until,
            description=reason,
            is_permanent=True if not until else False
        )

        officer.call(f'{player.name} was restricted. Reason: "{reason}"')
    else:
        # Player is online
        player.restrict(
            reason,
            until
        )

    return [f'{player.name} was restricted.']

@command(['unrestrict', 'unban'], ['Admins', 'Developers', 'Global Moderator Team'], hidden=False)
def unrestrict(ctx: Context) -> List | None:
    """<name> <restore scores (true/false)>"""

    if len(ctx.args) < 1:
        return [f'Invalid syntax: !{ctx.trigger} <name> <restore scores (true/false)>']

    username = ctx.args[0]
    restore_scores = True

    if len(ctx.args) > 1:
        restore_scores = eval(ctx.args[1].capitalize())

    if not (player := users.fetch_by_name(username)):
        return [f'Player "{username}" was not found.']

    if not player.restricted:
        return [f'Player "{username}" is not restricted.']

    users.update(player.id, {'restricted': False})

    # Add to player & supporter group
    groups.create_entry(player.id, 999)
    groups.create_entry(player.id, 1000)

    # Update hardware
    clients.update_all(player.id, {'banned': False})

    if not restore_scores:
        stats.delete_all(player.id)
        leaderboards.remove(player.id, player.country)
    else:
        scores.restore_hidden_scores(player.id)

    for user_stats in stats.fetch_all(player.id):
        leaderboards.update(
            user_stats,
            player.country
        )

    return [f'Player "{username}" was unrestricted.']

@command(['moderated'], ['Admins', 'Developers', 'Global Moderator Team'], hidden=False)
def moderated(ctx: Context) -> List | None:
    """<on/off>"""
    if len(ctx.args) != 1 and ctx.args[0] not in ('on', 'off'):
        return [f'Invalid syntax: !{ctx.trigger} <on/off>']

    if type(ctx.target) != Channel:
        return ['Target is not a channel.']

    ctx.target.moderated = ctx.args[0] == "on"

    return [f'Moderated mode is now {"enabled" if ctx.target.moderated else "disabled"}.']

@command(['kick', 'disconnect'], ['Admins', 'Developers', 'Global Moderator Team'], hidden=False)
def kick(ctx: Context) -> List | None:
    """<username>"""
    if len(ctx.args) <= 0:
        return [f'Invalid syntax: !{ctx.trigger} <username>']

    username = ' '.join(ctx.args[0:])

    if not (player := app.session.players.by_name(username)):
        return [f'User "{username}" was not found.']

    player.close_connection()

    return [f'{player.name} was disconnected from bancho.']

@command(['kill', 'close'], ['Admins', 'Developers', 'Global Moderator Team'], hidden=False)
def kill(ctx: Context) -> List | None:
    """<username>"""
    if len(ctx.args) <= 0:
        return [f'Invalid syntax: !{ctx.trigger} <username>']

    username = ' '.join(ctx.args[0:])

    if not (player := app.session.players.by_name(username)):
        return [f'User "{username}" was not found.']

    player.permissions = Permissions(255)
    player.enqueue_permissions()
    player.enqueue_ping()

    return [f'{player.name} was disconnected from bancho.']

@command(['multi', 'multiaccount', 'hardware'], ['Admins'])
def multi(ctx: Context) -> List | None:
    """<username>"""
    if len(ctx.args) <= 0:
        return [f'Invalid syntax: !{ctx.trigger} <username>']

    username = ' '.join(ctx.args[0:])

    if not (player := users.fetch_by_name(username)):
        return [f'User "{username}" was not found.']

    matches = {}

    for client in clients.fetch_all(player.id):
        hardware_matches = {
            match.user_id:match for match in
            clients.fetch_hardware_only(
                client.adapters,
                client.unique_id,
                client.disk_signature
            )
            if match.user_id != player.id
        }

        matches.update(hardware_matches)

    if not matches:
        return ['This user does not have any hardware matches with other accounts.']

    return [
        f'This user has {len(matches)} hardware {"match" if len(matches) == 1 else "matches"} with other accounts:',
        *[
            f"https://osu.{config.DOMAIN_NAME}/u/{user_id} {'(Banned)' if match.banned else ''}"
            for user_id, match in matches.items()
        ]
    ]

@command(['rtx', 'jumpscare'], ['Admins', 'Developers', 'Global Moderator Team'], hidden=False)
def rtx(ctx: Context) -> List | None:
    """<username> (<message>) - Zallius' eyes have awoken"""
    if len(ctx.args) <= 0:
        return [f'Invalid syntax: !{ctx.trigger} <username> (<message>)']

    username = ctx.args[0]
    message = "Zallius' eyes have awoken"
    target = app.session.players.by_name(username)

    if not target:
        return [f'User "{username}" was not found.']
    
    if len(ctx.args) > 1:
        message = ' '.join(ctx.args[1:])

    target.send_packet(target.packets.RTX, message)
    return [f"{target.name} was RTX'd."]

@command(['crash'], ['Admins', 'Developers'], hidden=False)
def crash(ctx: Context) -> List | None:
    """<username> - We do a little trolling"""
    if len(ctx.args) <= 0:
        return [f'Invalid syntax: !{ctx.trigger} <username>']
    
    username = " ".join(ctx.args[0:])
    target = app.session.players.by_name(username)

    if not target:
        return [f'User "{username}" was not found.']

    fake_match = bMatch(
        id=0,
        in_progress=False,
        type=MatchType.Standard,
        mods=Mods.NoMod,
        name="weeeeee",
        password="",
        beatmap_text="",
        beatmap_id=0,
        beatmap_checksum="",
        slots=[
            bSlot(player_id=2, status=SlotStatus.NotReady),
            *(bSlot(player_id=-index-1, status=SlotStatus.NoMap) for index in range(7))
        ],
        host_id=-1,
        mode=GameMode.Osu,
        scoring_type=MatchScoringTypes.Combo,
        team_type=MatchTeamTypes.HeadToHead,
        freemod=False,
        seed=13381
    )
    target.enqueue_match(fake_match)
    target.enqueue_matchjoin_success(fake_match)
    return [f"{target.name} was crashed, hopefully :tf:"]

# TODO: !rank
# TODO: !faq
# TODO: !top
