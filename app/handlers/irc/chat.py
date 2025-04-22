
from typing import List, Optional, Callable
from twisted.words.protocols import irc
from app.common.database import messages
from app.clients.irc import IrcClient
from app import session

import time

def register(command: str) -> Callable:
    def wrapper(func) -> Callable:
        session.irc_handlers[command] = func
        return func
    return wrapper

def ensure_authenticated(func: Callable) -> Callable:
    def wrapper(client: IrcClient, *args, **kwargs) -> None:
        if not client.logged_in:
            return
        return func(client, *args, **kwargs)
    return wrapper

@register("JOIN")
@ensure_authenticated
def handle_join_command(
    client: IrcClient,
    prefix: str,
    channel_name: str
) -> None:
    if not (channel := session.channels.by_name(channel_name)):
        client.enqueue_channel_revoked(channel_name)
        return

    channel.add(client)

@register("PRIVMSG")
def handle_privmsg_command(
    sender: IrcClient,
    prefix: str,
    target_name: str,
    message: str
) -> None:
    if not sender.logged_in:
        sender.token = message
        sender.handle_osu_login_callback()
        return

    if sender.silenced:
        sender.enqueue_command(irc.ERR_CANNOTSENDTOCHAN, [target])
        return

    if target_name.startswith("#"):
        channel = session.channels.by_name(target_name)

        if not channel:
            sender.enqueue_channel_revoked(target_name)
            return
        
        return channel.send_message(sender, message)

    if not (target := session.players.by_name_safe(target_name)):
        sender.enqueue_command(irc.ERR_NOSUCHNICK, [target_name])
        return

    if target.id == sender.id:
        sender.enqueue_command(irc.ERR_CANNOTSENDTOCHAN, [target_name])
        return

    if target.silenced:
        sender.enqueue_command(irc.ERR_CANNOTSENDTOCHAN, [target_name])
        return

    if target.friendonly_dms and sender.id not in target.friends:
        sender.enqueue_command(irc.ERR_CANNOTSENDTOCHAN, [target_name])
        return

    if (time.time() - sender.last_minute_stamp) > 60:
        sender.last_minute_stamp = time.time()
        sender.recent_message_count = 0

    if sender.recent_message_count > 30 and not sender.is_bot:
        return sender.silence(60, 'Chat spamming')

    target.enqueue_message(message, sender, sender.name)

    parsed_message = message.strip()
    has_command_prefix = parsed_message.startswith('!')

    if has_command_prefix or target is session.banchobot:
        return session.banchobot.send_command_response(
            *session.banchobot.process_command(parsed_message, sender, target)
        )

    if len(message) > 512:
        # Limit message size
        message = message[:497] + '... (truncated)'

    if target.away_message:
        sender.enqueue_message(
            f'\x01ACTION is away: {target.away_message}\x01',
            target,
            target.name
        )

    sender.recent_message_count += 1
    sender.logger.info(f'[PM -> {target.name}]: {message.content}')

    messages.create_private(
        sender.id,
        target.id,
        message.content[:512]
    )
