
from twisted.words.protocols import irc
from app.handlers.irc.decorators import *
from app.common.database import messages
from app.clients.irc import IrcClient
from app import session

import time

@register("LIST")
@ensure_authenticated
def handle_list_command(
    client: IrcClient,
    prefix: str,
    *args
) -> None:
    client.enqueue_command(
        irc.RPL_LISTSTART,
        "Channels :Users Name"
    )

    for channel in session.channels.values():
        if channel.public and channel.can_read(client.permissions):
            client.enqueue_command(
                irc.RPL_LIST,
                channel.name,
                f"{channel.user_count}",
                f":{channel.topic}"
            )

    client.enqueue_command(
        irc.RPL_LISTEND,
        ":End of /LIST"
    )

@register("TOPIC")
@ensure_authenticated
def handle_topic_command(
    client: IrcClient,
    prefix: str,
    channel_name: str,
    *args
) -> None:
    if not (channel := session.channels.by_name(channel_name)):
        client.enqueue_channel_revoked(channel_name)
        return

    if not channel.can_read(client.permissions):
        client.enqueue_channel_revoked(channel_name)
        return

    if not channel.topic:
        client.enqueue_command(
            irc.RPL_NOTOPIC,
            channel.name, ":No topic is set"
        )
        return

    client.enqueue_command(
        irc.RPL_TOPIC,
        channel.name,
        ":" + channel.topic
    )
    client.enqueue_command(
        "333", # RPL_TOPICWHOTIME
        channel.name,
        channel.owner,
        f'{int(channel.created_at)}'
    )

@register("JOIN")
@ensure_authenticated
def handle_join_command(
    client: IrcClient,
    prefix: str,
    channels: str
) -> None:
    for channel_name in channels.split(","):
        if not (channel := session.channels.by_name(channel_name)):
            client.enqueue_channel_revoked(channel_name)
            return

        if not channel.public and not client.is_staff:
            client.enqueue_channel_revoked(channel_name)
            return

        channel.add(client)

        if client not in channel.users:
            return

        client.enqueue_players(channel.users, channel.name)

@register("PART")
@ensure_authenticated
def handle_part_command(
    client: IrcClient,
    prefix: str,
    channels: str,
    *args
) -> None:
    for channel_name in channels.split(","):
        if not (channel := session.channels.by_name(channel_name)):
            client.enqueue_channel_revoked(channel_name)
            return

        channel.remove(client)

@register("MODE")
def handle_mode_command(
    client: IrcClient,
    prefix: str,
    *args
) -> None:
    if len(args) <= 0:
        return

    is_self = args[0] == client.local_prefix

    if is_self:
        return client.enqueue_command(irc.RPL_UMODEIS, "+i")

    if not (channel := session.channels.by_name(args[0])):
        return client.enqueue_command(irc.ERR_USERSDONTMATCH, ":Cannot change mode for this user")

    if len(args) > 1:
        return

    client.enqueue_command(
        irc.RPL_CHANNELMODEIS,
        channel.name,
        "+nt"
    )
    client.enqueue_command(
        "329", # RPL_CREATIONTIME
        channel.name,
        f'{int(channel.created_at)}'
    )

@register("PRIVMSG")
def handle_privmsg_command(
    sender: IrcClient,
    prefix: str,
    target_name: str,
    message: str
) -> None:
    if not sender.logged_in:
        sender.handle_osu_login_callback(message)
        return

    if sender.silenced:
        sender.enqueue_command(irc.ERR_CANNOTSENDTOCHAN, target, ":You are silenced.")
        return

    if target_name.startswith("#"):
        channel = session.channels.by_name(target_name)

        if not channel:
            sender.enqueue_channel_revoked(target_name)
            return
        
        return channel.send_message(sender, message)

    if not (target := session.players.by_name_safe(target_name)):
        sender.enqueue_command(irc.ERR_NOSUCHNICK, target_name, ":No such nick/channel")
        return

    if target.id == sender.id:
        sender.enqueue_command(irc.ERR_CANNOTSENDTOCHAN, target_name, ":You cannot send messages to yourself.")
        return

    if target.silenced:
        sender.enqueue_command(irc.ERR_CANNOTSENDTOCHAN, target_name, ":User is silenced.")
        return

    if target.friendonly_dms and sender.id not in target.friends:
        sender.enqueue_command(irc.ERR_CANNOTSENDTOCHAN, target_name, ":User is in friend-only mode.")
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
        return sender.enqueue_away_message(target)

    sender.recent_message_count += 1
    sender.logger.info(f'[PM -> {target.name}]: {message}')

    session.tasks.do_later(
        messages.create_private,
        sender.id,
        target.id,
        message
    )
