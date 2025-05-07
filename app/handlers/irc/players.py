
from twisted.words.protocols import irc
from app.handlers.irc.decorators import *
from app.clients.irc import IrcClient

import config
import app

@register("NAMES")
@ensure_authenticated
def handle_names_command(
    client: IrcClient,
    prefix: str,
    channel_names: str
) -> None:
    for channel_name in channel_names.split(","):
        if not (channel := app.session.channels.by_name(channel_name)):
            client.enqueue_channel_revoked(channel_name)
            return

        client.enqueue_players(
            channel.users,
            channel.name
        )

@register("WHO")
@ensure_authenticated
def handle_who_command(
    client: IrcClient,
    prefix: str,
    channel: str
) -> None:
    client.enqueue_command(
        irc.RPL_ENDOFWHO,
        params=[
            client.local_prefix,
            channel,
            f":End of /WHO list."
        ]
    )

@register("WHOIS")
@ensure_authenticated
def handle_whois_command(
    client: IrcClient,
    prefix: str,
    *args
) -> None:
    if len(args) <= 0:
        client.enqueue_command(
            irc.ERR_NOSUCHNICK,
            params=[client.local_prefix, ":No such nick/channel"]
        )
        return

    local_nickname = client.local_prefix
    target_nickname = args[-1]

    if not (target := app.session.players.by_name_safe(target_nickname)):
        client.enqueue_command(irc.ERR_NOSUCHNICK, params=[target_nickname, ":No such nick/channel"])
        return

    channel_names = [
        channel.name
        for channel in target.channels
        if channel.public
    ]

    client.enqueue_command(
        irc.RPL_WHOISUSER,
        params=[
            local_nickname,
            target_nickname,
            target.url,
            '*',
            f':{target.url}'
        ]
    )
    client.enqueue_command(
        irc.RPL_WHOISCHANNELS,
        params=[
            local_nickname,
            target_nickname,
            f":{' '.join(channel_names)}"
        ]
    )
    client.enqueue_command(
        irc.RPL_WHOISSERVER,
        params=[
            local_nickname,
            target_nickname,
            f'cho.{config.DOMAIN_NAME}',
            f':anchor',
        ]
    )
    client.enqueue_command(
        irc.RPL_ENDOFWHOIS,
        params=[
            local_nickname,
            target_nickname,
            f":End of /WHOIS list."
        ]
    )
