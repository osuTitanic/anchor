
from twisted.words.protocols import irc
from app.handlers.irc.decorators import *
from app.clients.irc import IrcClient
from config import DOMAIN_NAME

@register("QUIT")
def handle_quit(client: IrcClient, prefix: str, *args) -> None:
    client.close_connection()

@register("PING")
def handle_ping_command(
    client: IrcClient,
    prefix: str,
    *args
) -> None:
    client.enqueue_command_raw(
        "PONG",
        params=args
    )

@register("AWAY")
@ensure_authenticated
def handle_away_command(
    client: IrcClient,
    prefix: str,
    *args
) -> None:
    message = " ".join(args)

    if message:
        client.away_message = message
        client.away_senders.clear()
        client.enqueue_command(
            irc.RPL_NOWAWAY,
            ":You have been marked as being away"
        )
        return

    client.away_message = None
    client.enqueue_command(
        irc.RPL_UNAWAY,
        ":You are no longer marked as being away"
    )
