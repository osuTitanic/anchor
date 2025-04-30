

from typing import List, Optional, Callable
from twisted.words.protocols import irc
from app.clients.irc import IrcClient
from app import session

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

@register("NAMES")
@ensure_authenticated
def handle_names_command(
    client: IrcClient,
    prefix: str,
    channel_names: str
) -> None:
    for channel_name in channel_names.split(","):
        if not (channel := session.channels.by_name(channel_name)):
            client.enqueue_channel_revoked(channel_name)
            return

        client.enqueue_players(
            channel.users,
            channel.name
        )
