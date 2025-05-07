
from app.handlers.irc.decorators import *
from app.clients.irc import IrcClient
from app import session

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
