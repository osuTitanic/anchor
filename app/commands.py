
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

from .common.constants import Permissions, GameMode
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
        hidden: bool = True
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

@mp_commands.register(['help', 'h'])
def mp_help(ctx: Context):
    """- Shows this message"""
    response = []

    for command in mp_commands.commands:
        if not command.doc:
            continue

        response.append(f'!{mp_commands.trigger.upper()} {command.triggers[0].upper()} {command.doc}')

    return response

@mp_commands.register(['close', 'terminate', 'disband'], Permissions.Admin)
def mp_close(ctx: Context):
    """- Close a match and kick all players"""
    ctx.player.match.close()

    return ['Match was closed.']

@mp_commands.register(['abort'])
def mp_abort(ctx: Context):
    """- Abort the current match"""
    if not ctx.player.match.in_progress:
        return ["Nothing to abort."]

    ctx.player.match.abort()

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

    return [f'Selected: {map.link}']

# TODO: !system maintanance
# TODO: !system deploy
# TODO: !system restart
# TODO: !system shutdown
# TODO: !system stats
# TODO: !system exec

def command(
    aliases: List[str],
    p: Permissions = Permissions.Normal,
    hidden: bool = False,
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
