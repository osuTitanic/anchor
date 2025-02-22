
from app.commands import Context, Command, commands, sets
from app.common.database import users, groups, messages
from app.common.constants import Permissions
from app.objects.client import OsuClient
from app.common.objects import bMessage
from app.objects.channel import Channel
from app.objects.player import Player
from typing import Tuple, List

import shlex
import app

class BanchoBot(Player):
    def __init__(self):
        super().__init__('127.0.0.1', 6969)
        self.initialize()

    def process_command(
        self,
        message: str,
        sender: Player,
        target: Channel | Player
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

                ctx = Context(
                    ctx.player, trigger,
                    ctx.target, args
                )

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

        # Send to others
        if not command.hidden and type(context.target) is Channel:
            context.target.send_message(
                context.player,
                context.message
            )

            for message in response:
                context.target.send_message(self, message)

            return

        context.player.logger.info(f'[{context.player.name}]: {context.message}')
        context.player.logger.info(f'[{self.name}]: {", ".join(response)}')

        target_name = (
            context.target.name
            if type(context.target) != Channel
            else context.target.display_name
        )

        # Send to sender only
        for message in response:
            context.player.enqueue_message(
                bMessage(
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
        with app.session.database.managed_session() as session:
            self.object = users.fetch_by_id(1, session=session)
            self.client = OsuClient.empty()
            self.id = -self.object.id
            self.name = self.object.name
            self.stats  = self.object.stats
            self.client.ip.country_code = "OC"
            self.client.ip.city = "w00t p00t!"
            self.permissions = Permissions(
                groups.get_player_permissions(1, session=session)
            )
