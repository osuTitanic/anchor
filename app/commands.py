
from typing import List, Union, Optional, NamedTuple, Callable
from dataclasses import dataclass

from .common.database.repositories import (
    beatmapsets,
    users,
    logs
)

from .common.constants import Permissions
from .objects.channel import Channel
from .common.objects import bMessage
from .objects.player import Player

import traceback
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

commands: List[Command] = []
sets = [
    mp_commands := CommandSet('mp', 'Multiplayer Commands')
    # TODO: Add more...
]

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

@command(['help', 'h', ''], hidden=True)
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

        response.append(f'{set.doc} (!{set.trigger}):')

        for command in set.commands:
            if command.permissions not in ctx.player.permissions:
                continue

            response.append(
                f'!{command.triggers[0].upper()} {command.doc}'
            )

    return response

@command(['roll'])
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

@command(['report'], hidden=True)
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

@command(['search'], Permissions.Supporter)
def search(ctx: Context):
    """<query> - Search a beatmap"""
    query = ' '.join(ctx.args[0:])

    if len(query) <= 3:
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

@command(['monitor'], Permissions.Admin, hidden=True)
def monitor(ctx: Context) -> Optional[List]:
    """<name> - Monitor a player"""

    if len(ctx.args) < 1:
        return [f'Invalid syntax: !{ctx.trigger} <name>']

    name = ' '.join(ctx.args[0:])

    if not (player := app.session.players.by_name(name)):
        return ['Player is not online.']

    player.enqueue_monitor()

    return ['Player has been monitored.']

@command(['alert', 'announce', 'broadcast'], Permissions.Admin, hidden=True)
def alert(ctx: Context) -> Optional[List]:
    """<message> - Send a message to all players"""

    if not ctx.args:
        return [f'Invalid syntax: !{ctx.trigger} <message>']

    app.session.players.announce(' '.join(ctx.args))

    return [f'Alert was sent to {len(app.session.players)} players.']

@command(['alertuser'], Permissions.Admin, hidden=True)
def alertuser(ctx: Context) -> Optional[List]:
    """<username> <message> - Send a notification to a player"""

    if len(ctx.args) < 2:
        return [f'Invalid syntax: !{ctx.trigger} <username> <message>']

    username = ctx.args[0].replace('_', ' ')

    if not (player := app.session.players.by_name(username)):
        return [f'Could not find player "{username}".']

    player.enqueue_announcement(' '.join(ctx.args[1:]))

    return [f'Alert was sent to {player.name}.']

# TODO: !silence
# TODO: !unsilence
# TODO: !restrict
# TODO: !unrestrict
# TODO: !where
# TODO: !stats
# TODO: !rank
# TODO: !faq
# TODO: !moderated
# TODO: !kick
# TODO: !kill

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

    # Command sets
    for set in sets:
        for command in set.commands:
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
