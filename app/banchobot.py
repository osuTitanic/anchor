
from app.objects.channel import Channel, MultiplayerChannel
from app.commands import Context, Command, commands, sets
from app.objects.client import OsuClientInformation
from app.common.database import messages
from app.clients.irc import IrcClient
from app.clients.base import Client
from typing import Tuple, List
from chio import Message

import shlex
import app

class BanchoBot(IrcClient):
    def __init__(self):
        super().__init__('127.0.0.1', 13381)
        self.initialize()

    def process_command(
        self,
        message: str,
        sender: Client,
        target: Channel | Client
    ) -> Tuple[Context, Command, List[str]]:
        trigger, *args = self.parse_command(message)

        if not trigger:
            return None, None, []

        ctx = Context(sender, trigger, target, args)
        command = self.resolve_command(ctx)

        if not command:
            return ctx, None, []

        try:
            response = command.callback(ctx)
        except Exception as e:
            sender.logger.error(f'Command error: {e}', exc_info=e)
            response = ['An error occurred while running this command.']

        return ctx, command, response

    def parse_command(self, message: str) -> List[str]:
        if not message.startswith('!'):
            message = f'!{message}'

        try:
            trigger, *args = shlex.split(message.strip()[1:])
            trigger = trigger.lower()
            return trigger, *args
        except ValueError:
            return '', []

    def resolve_command(self, ctx: Context) -> Command | None:
        # Regular commands, e.g. !roll
        for command in commands:
            if ctx.trigger not in command.triggers:
                continue

            has_permissions = any(
                group in command.groups
                for group in ctx.player.groups
            )

            if not has_permissions:
                return

            return command

        if len(ctx.args) < 1:
            return

        set_trigger, trigger, *args = ctx.trigger, *ctx.args

        # Command sets, e.g. !mp invite <user>
        for set in sets:
            if set.trigger != set_trigger:
                continue

            for command in set.commands:
                if trigger not in command.triggers:
                    continue

                has_permissions = any(
                    group in command.groups
                    for group in ctx.player.groups
                )

                if not has_permissions:
                    continue

                ctx.trigger = trigger
                ctx.args = args
                ctx.set = set

                if not command.ignore_conditions:
                    # Check set conditions
                    for condition in set.conditions:
                        if not condition(ctx):
                            return
                        
                return command

    def send_command_response(
        self,
        context: Context,
        command: Command,
        response: List[str]
    ) -> None:
        if not response:
            return

        # Send to others, if command is not hidden
        if not command.hidden and context.target.is_channel:
            context.target.send_message(
                context.player,
                context.message,
                ignore_commands=True
            )

            for message in response:
                context.target.send_message(
                    self, message,
                    ignore_commands=True
                )

            return

        context.player.logger.info(f'[{context.player.name}]: {context.message}')
        context.player.logger.info(f'[{self.name}]: {", ".join(response)}')

        target_name = (
            context.target.name
            if not context.target.is_channel
            else context.target.display_name
        )

        if type(context.target) is MultiplayerChannel:
            target_name = context.target.resolve_name(context.player)

        # Send to sender only
        for message in response:
            context.player.enqueue_message_object(
                Message(
                    self.name, message,
                    target_name, self.id
                )
            )

        if context.target is not self:
            return

        # Store request/responses in database
        messages.create_private(
            context.player.id,
            self.object.id,
            context.message
        )

        messages.create_private(
            self.object.id,
            context.player.id,
            '\n'.join(response)
        )

    def initialize(self) -> None:
        self.id = 1
        self.name = "BanchoBot"
        self.info = OsuClientInformation.empty()
        self.presence.country_index = 1
        self.presence.city = "w00t p00t!"
        self.presence.is_irc = True
        self.reload()
        self.stats.rank = 0
