
from typing import List, Union, Optional, NamedTuple, Callable
from pytimeparse.timeparse import timeparse
from datetime import timedelta, datetime
from dataclasses import dataclass

from .common.cache import leaderboards
from .common.database.repositories import (
    beatmapsets,
    beatmaps,
    scores,
    stats,
    users,
    logs
)

from .common.constants import (
    MatchTeamTypes,
    Permissions,
    SlotStatus,
    SlotTeam,
    GameMode,
    Mods
)

from .objects.channel import Channel
from .common.objects import bMessage
from .objects.player import Player

import traceback
import timeago
import config
import random
import app

@dataclass
class Context:
    player: Player
    trigger: str
    target: Union[Channel, Player]
    args: List[str]

@dataclass
class CommandResponse:
    response: List[str]
    hidden: bool

class Command(NamedTuple):
    triggers: List[str]
    callback: Callable
    permissions: Permissions
    hidden: bool
    doc: Optional[str]

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
        p: Permissions = Permissions.Normal,
        hidden: bool = False
    ) -> Callable:
        def wrapper(f: Callable):
            self.commands.append(
                Command(
                    aliases,
                    f,
                    p,
                    hidden,
                    doc=f.__doc__
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

@mp_commands.condition
def inside_match(ctx: Context) -> bool:
    return ctx.player.match is not None

@mp_commands.condition
def is_host(ctx: Context) -> bool:
    return (ctx.player is ctx.player.match.host) or \
           (Permissions.Admin in ctx.player.permissions)

@mp_commands.register(['help', 'h'], hidden=True)
def mp_help(ctx: Context):
    """- Shows this message"""
    response = []

    for command in mp_commands.commands:
        if command.permissions not in ctx.player.permissions:
            continue

        if not command.doc:
            continue

        response.append(f'!{mp_commands.trigger.upper()} {command.triggers[0].upper()} {command.doc}')

    return response

@mp_commands.register(['close', 'terminate', 'disband'], Permissions.Admin)
def mp_close(ctx: Context):
    """- Close a match and kick all players"""
    ctx.player.match.close()
    ctx.player.match.logger.info('Match was closed by an admin.')

    return ['Match was closed.']

@mp_commands.register(['abort'])
def mp_abort(ctx: Context):
    """- Abort the current match"""
    if not ctx.player.match.in_progress:
        return ["Nothing to abort."]

    ctx.player.match.abort()
    ctx.player.match.logger.info('Match was aborted.')

    return ['Match aborted.']

@mp_commands.register(['map', 'setmap', 'beatmap'])
def mp_map(ctx: Context):
    """<beatmap_id> - Select a new beatmap by it's id"""
    if len(ctx.args) != 1 or not ctx.args[0].isdecimal():
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <beatmap_id>']

    match = ctx.player.match
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
    if len(ctx.args) != 1 or len(ctx.args[0]) % 2 != 0:
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <mods>']

    match = ctx.player.match
    mods = Mods.from_string(ctx.args[0])
    # TODO: Filter out invalid mods

    if mods == match.mods:
        return [f'Mods are already set to {match.mods.short}.']

    if match.freemod:
        # Set match mods
        match.mods = mods & ~Mods.FreeModAllowed

        # Set host mods
        match.host_slot.mods = mods & ~Mods.SpeedMods
    else:
        match.mods = mods

    match.logger.info(f'Updated match mods to {match.mods.short}.')

    match.update()
    return [f'Updated match mods to {match.mods.short}.']

@mp_commands.register(['freemod', 'fm', 'fmod'])
def mp_freemod(ctx: Context):
    """<on/off> - Enable or disable freemod status."""
    if len(ctx.args) != 1 or ctx.args[0] not in ("on", "off"):
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <on/off>']

    freemod = ctx.args[0] == 'on'
    match = ctx.player.match

    if match.freemod == freemod:
        return [f'Freemod is already {ctx.args[0]}.']

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
        # Keep mods from host
        match.mods |= match.host_slot.mods

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

    name = ' '.join(ctx.args[0:])
    match = ctx.player.match

    if not (target := match.get_player(name)):
        return ['Could not find this player.']

    match.host = target
    match.host.enqueue_match_transferhost()

    match.logger.info(f'Changed host to: {target.name}')
    match.update()

    return [f'{target.name} is now host of this match.']

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

    name = ' '.join(ctx.args[0:])
    match = ctx.player.match

    if name == app.session.bot_player.name:
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

@mp_commands.register(['force', 'forceinvite'], Permissions.Admin)
def mp_force_invite(ctx: Context):
    """<name> - Force a player to join this match"""
    if len(ctx.args) <= 0:
        return [f'Invalid syntax: !{mp_commands.trigger} {ctx.trigger} <name>']

    name = ' '.join(ctx.args[0:])
    match = ctx.player.match

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
    """Lock all unsued slots in the match."""
    for slot in ctx.player.match.slots:
        if slot.status == SlotStatus.Open:
            slot.status = SlotStatus.Locked

    ctx.player.match.update()
    return ['Locked all unused slots.']

@mp_commands.register(['unlock'])
def mp_unlock(ctx: Context):
    """Unlock all locked slots in the match."""
    for slot in ctx.player.match.slots:
        if slot.status == SlotStatus.Locked:
            slot.status = SlotStatus.Open

    ctx.player.match.update()
    return ['Locked all unused slots.']

# TODO: !system maintanance
# TODO: !system deploy
# TODO: !system restart
# TODO: !system shutdown
# TODO: !system stats
# TODO: !system exec

def command(
    aliases: List[str],
    p: Permissions = Permissions.Normal,
    hidden: bool = True,
) -> Callable:
    def wrapper(f: Callable) -> Callable:
        commands.append(
            Command(
                aliases,
                f,
                p,
                hidden,
                f.__doc__
            ),
        )
        return f
    return wrapper

@command(['help', 'h', ''])
def help(ctx: Context) -> Optional[List]:
    """- Shows this message"""
    response = []

    # Standard commands
    response.append('Standard Commands:')
    for command in commands:
        if command.permissions not in ctx.player.permissions:
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
                if command.permissions not in ctx.player.permissions:
                    continue

                if not command.doc:
                    continue

                response.append(
                    f'!{set.trigger.upper()} {command.triggers[0].upper()} {command.doc}'
                )

    return response

@command(['roll'], hidden=False)
def roll(ctx: Context) -> Optional[List]:
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
def report(ctx: Context) -> Optional[List]:
    """<username> <reason>"""
    if len(ctx.args) < 1:
        return [f'Invalid syntax: !{ctx.trigger} <username> (<reason>)']

    username = ctx.args[0].replace('_', ' ')

    if not (player := users.fetch_by_name(username)):
        return [f'Could not find player "{username}".']

    reason = ' '.join(ctx.args[1:])
    message = f'{ctx.player.name} reported {player.name} for: "{reason}".'

    if (player := app.session.players.by_id(player.id)):
        player.enqueue_monitor()

    logs.create(
        message,
        'info',
        'reports'
    )

    channel = app.session.channels.by_name('#admin')

    if channel:
        channel.send_message(
            app.session.bot_player,
            message
        )

    return ['Player was reported.']

@command(['search'], Permissions.Supporter, hidden=False)
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
    """<name> - Get the stats of a player"""
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

@command(['monitor'], Permissions.Admin)
def monitor(ctx: Context) -> Optional[List]:
    """<name> - Monitor a player"""

    if len(ctx.args) < 1:
        return [f'Invalid syntax: !{ctx.trigger} <name>']

    name = ' '.join(ctx.args[0:])

    if not (player := app.session.players.by_name(name)):
        return ['Player is not online']

    player.enqueue_monitor()

    return ['Player has been monitored']

@command(['alert', 'announce', 'broadcast'], Permissions.Admin)
def alert(ctx: Context) -> Optional[List]:
    """<message> - Send a message to all players"""

    if not ctx.args:
        return [f'Invalid syntax: !{ctx.trigger} <message>']

    app.session.players.announce(' '.join(ctx.args))

    return [f'Alert was sent to {len(app.session.players)} players.']

@command(['alertuser'], Permissions.Admin)
def alertuser(ctx: Context) -> Optional[List]:
    """<username> <message> - Send a notification to a player"""

    if len(ctx.args) < 2:
        return [f'Invalid syntax: !{ctx.trigger} <username> <message>']

    username = ctx.args[0].replace('_', ' ')

    if not (player := app.session.players.by_name(username)):
        return [f'Could not find player "{username}".']

    player.enqueue_announcement(' '.join(ctx.args[1:]))

    return [f'Alert was sent to {player.name}.']

@command(['silence', 'mute'], Permissions.Admin, hidden=False)
def silence(ctx: Context) -> Optional[List]:
    """<username> <duration> (<reason>)"""

    if len(ctx.args) < 2:
        return [f'Invalid syntax: !{ctx.trigger} <username> <duration> (<reason>)']

    name = ctx.args[0].replace('_', ' ')
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
            {
                'silence_end': player.silence_end
            }
        )

        silence_end = player.silence_end

    time_string = timeago.format(silence_end)
    time_string = time_string.replace('in ', '')

    # TODO: Infringements Table

    return [f'{player.name} was silenced for {time_string}']

@command(['unsilence', 'unmute'], Permissions.Admin, hidden=False)
def unsilence(ctx: Context):
    """- <username>"""

    if len(ctx.args) < 1:
        return [f'Invalid syntax: !{ctx.trigger} <name>']

    name = ctx.args[0].replace('_', ' ')

    if (player := app.session.players.by_name(name)):
        player.unsilence()
        return [f'{player.name} was unsilenced.']

    if not (player := users.fetch_by_name(name)):
        return [f'Player "{name}" was not found.']

    users.update(player.id, {'silence_end': None})

    return [f'{player.name} was unsilenced.']

@command(['restrict', 'ban'], Permissions.Admin, hidden=False)
def restrict(ctx: Context) -> Optional[List]:
    """<name> (<reason>)"""

    if len(ctx.args) < 1:
        return [f'Invalid syntax: !{ctx.trigger} <name> (<reason>)']

    username = ctx.args[0].replace('_', ' ')
    reason   = ' '.join(ctx.args[1:])

    if not (player := app.session.players.by_name(username)):
        # Player is not online, or was not found
        player = users.fetch_by_name(username)

        if not player:
            return [f'Player "{username}" was not found']

        player.restricted = True
        player.permissions = 0

        # Update user
        users.update(player.id,
            {
                'restricted': True,
                'permissions': 0
            }
        )
        leaderboards.remove(
            player.id,
            player.country
        )
        stats.delete_all(player.id)
        scores.hide_all(player.id)
    else:
        # Player is online
        player.restrict(reason)

    # TODO: Infringements Table

    return [f'{player.name} was restricted.']

@command(['unrestrict', 'unban'], Permissions.Admin, hidden=False)
def unrestrict(ctx: Context) -> Optional[List]:
    """<name> <restore scores (true/false)>"""

    if len(ctx.args) < 1:
        return [f'Invalid syntax: !{ctx.trigger} <name> <restore scores (true/false)>']

    username = ctx.args[0].replace('_', ' ')
    restore_scores = False

    if len(ctx.args) > 1:
        restore_scores = eval(ctx.args[1].capitalize())

    if not (player := users.fetch_by_name(username)):
        return [f'Player "{username}" was not found.']

    if not player.restricted:
        return [f'Player "{username}" is not restricted.']

    users.update(player.id,
        {
            'restricted': False,
            'permissions': 5 if config.FREE_SUPPORTER else 1
        }
    )

    if restore_scores:
        try:
            scores.restore_hidden_scores(player.id)
            stats.restore(player.id)
        except Exception as e:
            if config.DEBUG: traceback.print_exc()
            app.session.logger.error(
                f'Failed to restore scores of player "{player.name}": {e}'
            )
            return ['Failed to restore scores, but player was unrestricted.']

    return [f'Player "{username}" was unrestricted.']

# TODO: !rank
# TODO: !faq
# TODO: !moderated
# TODO: !kick
# TODO: !kill
# TODO: !top

def get_command(
    player: Player,
    target: Union[Channel, Player],
    message: str
) -> Optional[CommandResponse]:
    # Parse command
    trigger, *args = message.strip()[1:].split(' ')
    trigger = trigger.lower()

    # Regular commands
    for command in commands:
        if trigger in command.triggers:
            # Check permissions
            if command.permissions not in player.permissions:
                return None

            # Try running the command
            try:
                response = command.callback(
                    Context(
                        player,
                        trigger,
                        target,
                        args
                    )
                )
            except Exception as e:
                if config.DEBUG: traceback.print_exc()
                player.logger.error(f'Command error: {e}')

                response = ['An error occurred while running this command.']

            return CommandResponse(
                response,
                command.hidden
            )

    set_trigger, trigger, *args = trigger, *args

    # Command sets
    for set in sets:
        if set.trigger != set_trigger:
            continue

        for command in set.commands:
            if trigger in command.triggers:
                # Check permissions
                if command.permissions not in player.permissions:
                    return None

                ctx = Context(
                    player,
                    trigger,
                    target,
                    args
                )

                # Check set conditions
                for condition in set.conditions:
                    if not condition(ctx):
                        break
                else:
                    # Try running the command
                    try:
                        response = command.callback(ctx)
                    except Exception as e:
                        if config.DEBUG: traceback.print_exc()
                        player.logger.error(f'Command error: {e}')

                        response = ['An error occurred while running this command.']

                    return CommandResponse(
                        response,
                        command.hidden
                    )

    return None

def execute(
    player: Player,
    target: Union[Channel, Player],
    command_message: str
):
    if not command_message.startswith('!'):
        command_message = f'!{command_message}'

    command = get_command(
        player,
        target,
        command_message
    )

    if not command:
        return

    # Send to others
    if not command.hidden and type(target) == Channel:
        target.send_message(
            player,
            command_message
        )

        for message in command.response:
            target.send_message(
                app.session.bot_player,
                message
            )
        return

    player.logger.info(f'[{player.name}]: {command_message}')
    player.logger.info(f'[{app.session.bot_player.name}]: {", ".join(command.response)}')

    target_name = target.name \
        if type(target) == Player \
        else target.display_name

    # Send to sender
    for message in command.response:
        player.enqueue_message(
            bMessage(
                app.session.bot_player.name,
                message,
                target_name,
                app.session.bot_player.id
            )
        )
