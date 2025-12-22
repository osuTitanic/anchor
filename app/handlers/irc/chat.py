
from twisted.words.protocols import irc
from app.handlers.irc.decorators import *
from app.common.database import messages
from app.clients.irc import IrcClient
from app.common import officer
from app import session

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
        if channel.public and channel.can_read(client):
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
    channel_name: str = None,
    *args
) -> None:
    if not channel_name:
        client.enqueue_command(irc.ERR_NEEDMOREPARAMS, "TOPIC", ":Not enough parameters")
        return

    if not (channel := session.channels.by_name(channel_name)):
        client.enqueue_channel_revoked(channel_name)
        return

    if not channel.can_read(client):
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
    channels: str = None
) -> None:
    if not channels:
        client.enqueue_command(irc.ERR_NEEDMOREPARAMS, "JOIN", ":Not enough parameters")
        return

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

        session.tasks.do_later(
            client.enqueue_players,
            channel.users,
            channel.name,
            priority=2
        )

@register("PART")
@ensure_authenticated
def handle_part_command(
    client: IrcClient,
    prefix: str,
    channels: str = None,
    *args
) -> None:
    if not channels:
        client.enqueue_command(irc.ERR_NEEDMOREPARAMS, "PART", ":Not enough parameters")
        return

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
        client.enqueue_command(irc.ERR_NEEDMOREPARAMS, "MODE", ":Not enough parameters")
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
    target_name: str = None,
    message: str = None,
    *args
) -> None:
    if not sender.logged_in:
        sender.handle_osu_login_callback(message)
        return

    if not target_name:
        sender.enqueue_command(irc.ERR_NORECIPIENT, ":No recipient given (PRIVMSG)")
        return

    if not message:
        sender.enqueue_command(irc.ERR_NOTEXTTOSEND, ":No text to send")
        return

    if sender.silenced:
        sender.enqueue_command(irc.ERR_CANNOTSENDTOCHAN, target_name, ":You are silenced.")
        return

    if target_name.startswith("#"):
        channel = session.channels.by_name(target_name)

        if not channel:
            sender.enqueue_channel_revoked(target_name)
            return

        channel.send_message(sender, message)
        return

    if not (target := session.players.by_name_safe(target_name)):
        sender.enqueue_command(irc.ERR_NOSUCHNICK, target_name, ":No such nick/channel")
        return

    if target.id == sender.id:
        sender.enqueue_command(irc.ERR_NOSUCHNICK, target_name, ":You cannot send messages to yourself.")
        return

    if target.silenced:
        sender.enqueue_command(irc.ERR_NOSUCHNICK, target_name, ":User is silenced.")
        return

    if target.friendonly_dms and sender.id not in target.friends:
        sender.enqueue_command(irc.ERR_NOSUCHNICK, target_name, ":User is in friend-only mode.")
        return

    if not sender.is_bot and not sender.message_limiter.allow():
        sender.silence(60, 'Chat spamming')
        return

    # Apply chat filters to the message
    message, timeout = session.filters.apply(message)

    if timeout is not None:
        sender.silence(timeout, 'Inappropriate discussion in pms')
        officer.call(f"Message: {message}")
        return

    parsed_message = message.strip()
    has_command_prefix = parsed_message.startswith('!')

    if has_command_prefix or target is session.banchobot:
        return session.tasks.do_later(
            session.banchobot.process_and_send_response,
            parsed_message, sender, target, priority=3
        )

    if len(message) > 512:
        # Limit message size
        message = message[:497] + '... (truncated)'

    target.enqueue_message(
        message,
        sender,
        sender.name
    )

    sender.logger.info(
        f'[PM -> {target.name}]: {message}'
    )

    session.tasks.do_later(
        messages.create_private,
        sender.id,
        target.id,
        message,
        priority=4
    )

    if target.away_message:
        return sender.enqueue_away_message(target)
