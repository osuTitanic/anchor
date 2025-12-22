
from twisted.words.protocols import irc
from app.handlers.irc.decorators import *
from app.clients.irc import IrcClient
from app import session

@register("USER")
@ensure_unauthenticated
def handle_user_command(
    client: IrcClient,
    prefix: str,
    username: str = None,
    hostname: str = "",
    servername: str = "",
    realname: str = ""
) -> None:
    if not username:
        client.enqueue_command(irc.ERR_NEEDMOREPARAMS, "USER", ":Not enough parameters")
        return

    client.is_osu = (
        (realname == "osu" or realname.isdigit()) and
        hostname == "False" and
        servername == "*" and
        username == "OSU" and
        prefix == ""
    )

@register("PASS")
@ensure_unauthenticated
def handle_pass_command(
    client: IrcClient,
    prefix: str,
    token: str = None
) -> None:
    if not token:
        client.enqueue_command(irc.ERR_NEEDMOREPARAMS, "PASS", ":Not enough parameters")
        return

    client.token = token

    if client.name != "":
        client.on_login_received()

@register("NICK")
@ensure_unauthenticated
def handle_nick_command(
    client: IrcClient,
    prefix: str,
    nickname: str = None
) -> None:
    if not nickname:
        client.enqueue_command(irc.ERR_NONICKNAMEGIVEN, ":No nickname given")
        return

    client.name = nickname.lower()

    if client.is_osu:
        client.name = client.name.removesuffix("-osu")

    if client.name == session.banchobot.name.lower():
        client.enqueue_banchobot_message("no.")
        client.close_connection("Tried to log in as BanchoBot.")
        return

    if client.is_osu and not client.token:
        # Let user enter in their token via. chat
        return client.handle_osu_login()

    if client.token != "":
        return client.on_login_received()
