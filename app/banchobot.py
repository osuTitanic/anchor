
from app.objects.channel import Channel, MultiplayerChannel
from app.commands import Context, Command, commands, sets
from app.common.config import config_instance as config
from app.common.helpers import permissions
from app.common.database import messages
from app.clients.irc import IrcClient
from app.clients.base import Client

from typing import Tuple, List, Iterable
from collections import defaultdict
from mistralai import Mistral
from chio import Message

import shlex
import time
import app

class BanchoBot(IrcClient):
    def __init__(self):
        super().__init__('127.0.0.1', 13381)
        self.id = 1
        self.name = "BanchoBot"
        self.presence.city = "w00t p00t!"
        self.presence.country_index = 1
        self.logged_in = True

        # Mistral integration for banchobot
        self.sdk = None
        self.conversations = defaultdict(list)

        if not config.MISTRAL_API_KEY:
            return

        self.sdk = Mistral(
            api_key=config.MISTRAL_API_KEY,
            server_url=config.MISTRAL_SERVER_URL,
            timeout_ms=config.MISTRAL_TIMEOUT_MS
        )

    def process_and_send_response(
        self,
        message: str,
        sender: Client,
        target: Channel | Client
    ) -> None:
        self.send_command_response(
            *self.process_command(message, sender, target)
        )

    def process_command(
        self,
        message: str,
        sender: Client,
        target: Channel | Client
    ) -> Tuple[Context | None, Command | None, List[str]]:
        trigger, *args = self.parse_command(message)

        if not trigger:
            return None, None, []

        ctx = Context(sender, trigger, target, args)
        command = self.resolve_command(ctx)

        if not command:
            if not self.sdk:
                return ctx, None, []

            if target is not self:
                return ctx, None, []

            response = self.handle_conversation(ctx)
            return ctx, None, response or []

        try:
            response = command.callback(ctx)
        except Exception as e:
            sender.logger.error(f'Command error: {e}', exc_info=e)
            response = ['An error occurred while running this command.']

        return ctx, command, response

    def parse_command(self, message: str) -> Iterable[str]:
        safe_message = message.strip()

        if not safe_message.startswith('!'):
            safe_message = f'!{safe_message}'

        try:
            trigger, *args = shlex.split(safe_message[1:])
            trigger = trigger.lower()
            return trigger, *args
        except ValueError:
            return '', []

    def resolve_command(self, ctx: Context) -> Command | None:
        # Regular commands, e.g. !roll
        for command in commands:
            if ctx.trigger.lower() not in command.triggers:
                continue

            has_permission = permissions.has_permission(
                permission=command.permission,
                user_id=ctx.player.id
            )

            if not has_permission:
                return

            return command

        if len(ctx.args) < 1:
            return

        set_trigger, trigger, *args = ctx.trigger, *ctx.args

        # Command sets, e.g. !mp invite <user>
        for set in sets:
            if set.trigger.lower() != set_trigger:
                continue

            for command in set.commands:
                if trigger.lower() not in command.triggers:
                    continue

                has_permission = permissions.has_permission(
                    permission=command.permission,
                    user_id=ctx.player.id
                )

                if not has_permission:
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
        command: Command | None,
        response: List[str]
    ) -> None:
        if not response:
            return

        # Update BanchoBot's activity timestamp
        self.update_activity_later()

        # Send to all users in the channel, if command is not hidden
        if (
            command is not None
            and not command.hidden
            and context.target.is_channel
        ):
            context.target.send_message(
                context.player,
                context.message,
                ignore_commands=True,
                do_later=False
            )
            context.target.send_message(
                self, "\n".join(response),
                ignore_commands=True,
                do_later=False
            )
            return

        # The command is hidden, so we send it only to the player
        context.player.logger.info(f'[{context.player.name}]: {context.message}')
        context.player.logger.info(f'[{self.name}]: {"\n".join(response)}')

        target_name = (
            context.target.name
            if not context.target.is_channel
            else context.target.display_name
        )

        if context.is_multiplayer:
            # Referee players & regular players get different channel names
            target_name = context.target.resolve_name(context.player)

        for message in response:
            context.player.enqueue_message_object(
                Message(
                    self.name, message,
                    target_name, self.id
                )
            )

        # Check if we are in DMs
        if context.target is not self:
            return

        # Store DM request/responses in database
        app.session.tasks.do_later(
            self.store_to_database,
            context,
            response,
            priority=4
        )

    def handle_conversation(self, ctx: Context) -> List[str]:
        if not self.sdk or ctx.target is not self:
            return []

        entry = {
            "message": ctx.message.removeprefix('!'),
            "response": "",
            "timestamp": time.time()
        }
        conversation = self.conversations[ctx.player.id]
        conversation.append(entry)

        messages = []

        for index, item in enumerate(conversation):
            messages.append({
                "role": "user",
                "content": f"{ctx.player.name}: '{item['message']}'",
                "prefix": index == len(conversation) - 1
            })

            if not item.get("response"):
                continue

            messages.append({
                "role": "assistant",
                "content": item["response"]
            })

        try:
            response = self.sdk.agents.complete(
                messages=messages,
                agent_id=config.MISTRAL_AGENT_ID,
                max_tokens=config.MISTRAL_MAX_TOKENS
            )

            replies = [
                choice.message.content
                for choice in response.choices
                if choice.message and choice.message.content
            ]

            if replies:
                entry["response"] = "\n".join(replies)

            return replies
        except Exception as e:
            ctx.player.logger.error(f'Mistral request failed: {e}', exc_info=e)
            conversation.pop()
            return []

    def store_to_database(self, context: Context, response: List[str]) -> None:
        with app.session.database.managed_session() as session:
            messages.create_private(
                context.player.id,
                self.object.id,
                context.message,
                session=session
            )
            messages.create_private(
                self.object.id,
                context.player.id,
                '\n'.join(response),
                session=session
            )

    """Method stubs for 'IrcClient' default class behavior"""

    def update_object(self, mode: int = 0) -> None:
        super().update_object(mode)
        self.stats.rank = 0

    def reload_rankings(self) -> None:
        self.rankings = {"global": 0}

    def apply_ranking(self, ranking: str = 'global') -> None:
        pass

    def reload_rank(self) -> None:
        pass
