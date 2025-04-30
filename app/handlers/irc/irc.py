
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

@register("QUIT")
def handle_quit(client: IrcClient, prefix: str, *args) -> None:
    client.close_connection()
