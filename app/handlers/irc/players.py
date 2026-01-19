
from twisted.words.protocols import irc
from app.handlers.irc.decorators import *
from app.clients.irc import IrcClient
from app.session import config

import app

@register("NAMES")
@ensure_authenticated
def handle_names_command(
    client: IrcClient,
    prefix: str,
    channel_names: str = None,
    *args
) -> None:
    if not channel_names:
        client.enqueue_command(irc.ERR_NEEDMOREPARAMS, "NAMES", ":Not enough parameters")
        return

    for channel_name in channel_names.split(","):
        if not (channel := app.session.channels.by_name(channel_name)):
            client.enqueue_channel_revoked(channel_name)
            return

        app.session.tasks.do_later(
            client.enqueue_players,
            channel.users,
            channel.name,
            priority=3
        )

@register("WHO")
@ensure_authenticated
def handle_who_command(
    client: IrcClient,
    prefix: str,
    target: str = None,
    *args
) -> None:
    if not target:
        client.enqueue_command(irc.ERR_NEEDMOREPARAMS, "WHO", ":Not enough parameters")
        return

    is_channel = target.startswith("#")
    handler = handle_channel_who if is_channel else handle_user_who
    handler(client, target)

    client.enqueue_command(
        irc.RPL_ENDOFWHO,
        target,
        f":End of /WHO list."
    )

def handle_channel_who(
    client: IrcClient,
    channel_name: str
) -> None:
    if not (channel := app.session.channels.by_name(channel_name)):
        return

    # Send RPL_WHOREPLY for each user in the channel
    for user in channel.users:
        if user.hidden and user != client:
            continue

        away_flag = "G" if user.away_message else "H"
        status = away_flag + user.irc_prefix

        # Format: <channel> <user> <host> <server> <nick> <H|G>[*][@|+] :<hopcount> <real name>
        client.enqueue_command(
            irc.RPL_WHOREPLY,
            channel_name,
            user.safe_name,
            f"cho.{config.DOMAIN_NAME}",
            f"cho.{config.DOMAIN_NAME}",
            client.resolve_username(user),
            status,
            f":0 {user.name}"
        )

def handle_user_who(
    client: IrcClient,
    nickname: str
) -> None:
    if not (user := app.session.players.by_name_safe(nickname)):
        return

    # Find a common channel or use * if none
    common_channel = "*"

    for channel in user.channels:
        if channel.public and client in channel.users:
            common_channel = channel.name
            break

    away_flag = "G" if user.away_message else "H"
    status = away_flag + user.irc_prefix

    # Format: <channel> <user> <host> <server> <nick> <H|G>[*][@|+] :<hopcount> <real name>
    client.enqueue_command(
        irc.RPL_WHOREPLY,
        common_channel,
        user.safe_name,
        f"cho.{config.DOMAIN_NAME}",
        f"cho.{config.DOMAIN_NAME}",
        client.resolve_username(user),
        status,
        f":0 {user.name}"
    )

@register("ISON")
@ensure_authenticated
def handle_ison_command(
    client: IrcClient,
    prefix: str,
    *nicknames: str
) -> None:
    if len(nicknames) <= 0:
        client.enqueue_command(irc.ERR_NEEDMOREPARAMS, "ISON", ":Not enough parameters")
        return

    online: list[str] = []

    for nickname in nicknames:
        if not nickname:
            continue

        if not (player := app.session.players.by_name_safe(nickname)):
            continue

        if player.hidden and player != client:
            continue

        online.append(client.resolve_username(player))

    client.enqueue_command(irc.RPL_ISON, ":" + " ".join(online))

@register("USERHOST")
@ensure_authenticated
def handle_userhost_command(
    client: IrcClient,
    prefix: str,
    *nicknames: str
) -> None:
    if len(nicknames) <= 0:
        client.enqueue_command(irc.ERR_NEEDMOREPARAMS, "USERHOST", ":Not enough parameters")
        return

    host = f"cho.{config.DOMAIN_NAME}"
    replies: list[str] = []

    for nickname in nicknames[:5]:
        if not nickname:
            continue

        if not (player := app.session.players.by_name_safe(nickname)):
            continue

        if player.hidden and player != client:
            continue

        nick = client.resolve_username(player)
        oper_flag = "*" if player.is_staff else ""
        away_flag = "-" if player.away_message else "+"
        user = player.safe_name
        replies.append(f"{nick}{oper_flag}={away_flag}{user}@{host}")

    client.enqueue_command(irc.RPL_USERHOST, ":" + " ".join(replies))

@register("WHOIS")
@ensure_authenticated
def handle_whois_command(
    client: IrcClient,
    prefix: str,
    *target_nicknames
) -> None:
    if len(target_nicknames) <= 0:
        client.enqueue_command(
            irc.ERR_NEEDMOREPARAMS,
            "WHOIS",
            f":Not enough parameters"
        )
        return

    last_target = None

    for nickname in target_nicknames:
        if nickname == f'cho.{config.DOMAIN_NAME}':
            continue

        if not (target := app.session.players.by_name_safe(nickname)):
            client.enqueue_command(irc.ERR_NOSUCHNICK, nickname, ":No such nick/channel")
            return

        channel_names = [
            channel.name
            for channel in target.channels
            if channel.public
        ]
        last_target = target

        client.enqueue_command(
            irc.RPL_WHOISUSER,
            target.underscored_name,
            target.safe_name,
            f"cho.{config.DOMAIN_NAME}",
            '*',
            f':{target.url}'
        )

        if target.away_message:
            client.enqueue_command(
                irc.RPL_AWAY,
                target.underscored_name,
                f":{target.away_message}"
            )

        client.enqueue_command(
            irc.RPL_WHOISCHANNELS,
            target.underscored_name,
            f":{' '.join(channel_names)}"
        )
        client.enqueue_command(
            irc.RPL_WHOISSERVER,
            target.underscored_name,
            f'cho.{config.DOMAIN_NAME}',
            f':anchor',
        )

        if target.is_staff:
            client.enqueue_command(
                irc.RPL_WHOISOPERATOR,
                target.underscored_name,
                f":is an IRC operator"
            )

    if last_target:
        client.enqueue_command(
            irc.RPL_ENDOFWHOIS,
            last_target.underscored_name,
            f":End of /WHOIS list."
        )
