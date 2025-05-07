
from app.handlers.irc.decorators import *
from app.clients.irc import IrcClient

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
