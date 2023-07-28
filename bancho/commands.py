
from typing import Optional, NamedTuple, Callable, Union, List, Any
from pytimeparse.timeparse import timeparse
from datetime import datetime, timedelta
from dataclasses import dataclass

from bancho.common.objects import DBUser, DBScore, DBStats

from .constants import Permissions, ResponsePacket
from .objects.channel import Channel
from .objects.player import Player

import traceback
import random
import bancho

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
    mp_commands := CommandSet('mp', 'Multiplayer Commands'),
    bm_commands := CommandSet('bm', 'Beatmap Commands')
]

def command(
    aliases: list[str],
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
        # User set a custom roll number
        max_roll = min(int(ctx.args[0]), 0x7FFF)
    
    if max_roll <= 0:
        return ['no.']
    
    return [f'{ctx.player.name} rolls {random.randrange(0, max_roll+1)} points!']

@command(['report'], hidden=True)
def report(ctx: Context) -> Optional[List]:
    """<username> <reason>"""
    if len(ctx.args) < 2:
        return [f'Invalid syntax: !{ctx.trigger} <username> <reason>']

    username = ctx.args[0].replace('_', ' ')

    if not (player := bancho.services.database.user_by_name(username)):
        return ['Could not find user.']

    reason = ' '.join(ctx.args[1:])
    message = f'{ctx.player.name} reported {player.name} for: "{reason}".'

    if (player := bancho.services.players.by_id(player.id)):
        player.handler.enqueue_monitor()

    bancho.services.database.submit_log(
        message,
        'info',
        'reports'
    )

    channel = bancho.services.channels.by_name('#admin')

    if channel:
        channel.send_message(
            bancho.services.bot_player,
            message
        )

    return ['Player was reported.']

@command(['alert', 'announce', 'broadcast'], Permissions.Admin, hidden=True)
def alert(ctx: Context) -> Optional[List]:
    """<message> - Send a message to all players"""

    if not ctx.args:
        return [f'Invalid syntax: !{ctx.trigger} <message>']

    bancho.services.players.announce(' '.join(ctx.args))

    return [f'Alert was sent to {len(bancho.services.players)} players.']

@command(['alertuser'], Permissions.Admin, hidden=True)
def alertuser(ctx: Context) -> Optional[List]:
    """<username> <message> - Send a notification to a player"""
    
    if len(ctx.args) < 2:
        return [f'Invalid syntax: !{ctx.trigger} <username> <message>']
    
    username = ctx.args[0].replace('_', ' ')
    
    if not (player := bancho.services.players.by_name(username)):
        return ['Could not find user.']
    
    player.handler.enqueue_announcement(' '.join(ctx.args[1:]))

    return [f'Alert was sent to {player.name}.']

@command(['restrict', 'ban'], Permissions.Admin)
def restrict(ctx: Context) -> Optional[List]:
    """<name> (<reason>)"""

    if len(ctx.args) < 1:
        return [f'Invalid syntax: !{ctx.trigger} <name> (<reason>)']

    username = ctx.args[0].replace('_', ' ')
    reason   = None

    if not (player := bancho.services.players.by_name(username)):
        # Player is not online, or was not found
        player = bancho.services.database.user_by_name(username)

        if not player:
            return [f'Player "{username}" was not found']
        
        player.restricted = True
        player.permissions = 0

        # Update user
        instance = bancho.services.database.session
        instance.query(DBUser).filter(DBUser.id == player.id).update(
            {
                'restricted': True,
                'permissions': 0
            }
        )
        # Remove stats
        instance.query(DBStats).filter(DBStats.user_id == player.id).delete()
        # Hide scores
        instance.query(DBScore).filter(DBScore.user_id == player.id).update(
            {'status': -1}
        )
        instance.commit()

    else:
        # Player is online
        if len(ctx.args) > 1:
            reason = ' '.join(ctx.args[1:])

        player.restrict(reason)

    return [f'{player.name} was restricted.']

@command(['unrestrict', 'unban'], Permissions.Admin)
def unrestrict(ctx: Context) -> Optional[List]:
    """<name>"""

    if len(ctx.args) < 1:
        return [f'Invalid syntax: !{ctx.trigger} <name>']
    
    username = ctx.args[0].replace('_', ' ')

    if not (player := bancho.services.database.user_by_name(username)):
        return [f'Player "{username}" was not found.']
    
    if not player.restricted:
        return [f'Player "{username}" is not restricted.']

    bancho.services.database.restore_hidden_scores(player.id)
    bancho.services.database.restore_stats(player.id)

    instance = bancho.services.database.session
    instance.query(DBUser) \
            .filter(DBUser.id == player.id) \
            .update({
                'restricted': False,
                'permissions': 1
            })
    instance.commit()

    return [f'Player "{username}" was unrestricted.']

@command(['silence', 'mute'], Permissions.Admin)
def silence(ctx: Context) -> Optional[List]:
    """<name> <duration> (<reason>)"""

    if len(ctx.args) < 2:
        return [f'Invalid syntax: !{ctx.trigger} <name> <duration> (<reason>)']
    
    duration = timeparse(ctx.args[1])
    reason   = " ".join(ctx.args[2:])
    name     = ctx.args[0].replace('_', ' ')

    if (player := bancho.services.players.by_name(name)):
        # Player is online
        player.silence(duration, reason)
    else:
        # Player is offline, or was not found
        player = bancho.services.database.user_by_name(name)

        if not player:
            return [f'Player "{name}" was not found.']
        
        instance = bancho.services.database.session

        if player.silence_end:
            # If player was silenced before, append the duration
            instance.query(DBUser).filter(DBUser.id == player.id).update(
                {
                    'silence_end': player.silence_end + timedelta(seconds=duration)
                }
            )
        else:
            instance.query(DBUser).filter(DBUser.id == player.id).update(
                {
                    'silence_end': datetime.now() + timedelta(seconds=duration)
                }
            )
        instance.commit()

    return [f'{player.name} was silenced.']

@command(['unsilence', 'unmute'], Permissions.Admin)
def unsilence(ctx: Context) -> Optional[List]:
    """<name>"""
    
    if len(ctx.args) < 1:
        return [f'Invalid syntax: !{ctx.trigger} <name>']
    
    name = ctx.args[0].replace('_', ' ')
    
    if (player := bancho.services.players.by_name(name)):
        # Player is online
        player.unsilence()

    else:
        # Player is offline, or was not found
        player = bancho.services.database.user_by_name(name)

        if not player:
            return [f'Player "{name}" was not found.']

        # Player is offline, or was not found
        instance = bancho.services.database.session
        instance.query(DBUser).filter(DBUser.id == player.id).update(
            {
                'silence_end': None
            }
        )
        instance.commit()
    
    return [f'{player.name} was unsilenced.']

@command(['monitor'], Permissions.Admin, hidden=True)
def monitor(ctx: Context) -> Optional[List]:
    """<name>"""
    
    if len(ctx.args) < 1:
        return [f'Invalid syntax: !{ctx.trigger} <name>']

    name = ctx.args[0].replace('_', ' ')
    
    if not (player := bancho.services.players.by_name(name)):
        return ['Player was not found.']
    
    player.handler.enqueue_monitor()
    
    return ['Player has been monitored.']

# TODO: !mp ...
# TODO: !bm ...

def get_command(
    player: Player,
    target: Union[Channel, Player],
    message: str
) -> Optional[CommandResponse]:
    # Check for prefix
    if not message.strip().startswith('!'):
        if target != bancho.services.bot_player:
            return None

        message = f'!{message}'

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
                traceback.print_exc()
                player.logger.error(f'Command error: {e}')

                response = ['An error occurred when running this command.']

            return CommandResponse(
                response,
                command.hidden
            )
        
    # Command sets
    for set in sets:
        for command in set:
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
                    traceback.print_exc()
                    player.logger.error(f'Command error: {e}')
    
                    response = ['An error occurred when running this command.']
    
                return CommandResponse(
                    response,
                    command.hidden
                )
        
    return None
