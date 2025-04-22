
from typing import List, Optional, Callable
from twisted.words.protocols import irc
from app.clients.irc import IrcClient
from app import session

def register(command: str) -> Callable:
    def wrapper(func) -> Callable:
        session.irc_handlers[command] = func
        return func
    return wrapper

@register("PING")
def handle_ping_command(
    client: IrcClient,
    prefix: str,
    *args
) -> None:
    client.enqueue_command(
        "PONG",
        prefix, args
    )

@register("NAMES")
def handle_names_command(
    client: IrcClient,
    prefix: str,
    channel_name: str
) -> None:
    if not (channel := session.channels.by_name(channel_name)):
        client.enqueue_channel_revoked(channel_name)
        return

    client.enqueue_players(
        channel.users,
        channel.name
    )

@register("MODE")
def handle_mode_command(
    client: IrcClient,
    prefix: str,
    channel_name: str,
    *args
) -> None:
    if not (channel := session.channels.by_name(channel_name)):
        client.enqueue_channel_revoked(channel_name)
        return

    client.enqueue_mode(channel)

@register("QUIT")
def handle_quit(client: IrcClient, prefix: str, *args) -> None:
    client.close_connection()
