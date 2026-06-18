
from app.handlers.irc.decorators import register
from app.clients.irc import IrcClient

# CAP lets clients discover and request optional server features before completing registration.
# Since we support no capabilities, we advertise an empty list (CAP * LS :) & NAK every REQ.
# This should be enough to make all standard IRC clients work.

# TODO: We might want to add sasl support so users can authenticate without sending their IRC token in the PASS packet

@register("CAP")
def handle_cap(client: IrcClient, prefix: str, subcommand: str = None, *args) -> None:
    if not subcommand:
        return

    subcommand = subcommand.upper()

    match subcommand:
        case "LS":
            client.enqueue_command_raw("CAP", params=["*", "LS", ""])
        case "LIST":
            client.enqueue_command_raw("CAP", params=["*", "LIST", ""])
        case "REQ":
            requested = args[0] if args else ""
            client.enqueue_command_raw("CAP", params=["*", "NAK", requested])
        case "END":
            pass
        case _:
            client.enqueue_command_raw("410", params=["*", subcommand, ":Invalid CAP subcommand"])
