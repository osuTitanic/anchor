
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
    channel_names: str = None
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
    channel: str = None
) -> None:
    if not channel:
        client.enqueue_command(irc.ERR_NEEDMOREPARAMS, "WHO", ":Not enough parameters")
        return

    client.enqueue_command(
        irc.RPL_ENDOFWHO,
        channel,
        f":End of /WHO list."
    )

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
            target.url,
            '*',
            f':{target.url}'
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
