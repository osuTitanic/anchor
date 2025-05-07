
from config import OSU_IRC_ENABLED
from typing import List, Optional, Callable
from app.clients.irc import IrcClient
from app import session

def register(command: str) -> Callable:
    def wrapper(func) -> Callable:
        session.irc_handlers[command] = func
        return func
    return wrapper

def ensure_unauthenticated(func: Callable) -> Callable:
    def wrapper(client: IrcClient, *args, **kwargs) -> None:
        if client.logged_in:
            return
        return func(client, *args, **kwargs)
    return wrapper

@register("USER")
@ensure_unauthenticated
def handle_user_command(
    client: IrcClient,
    prefix: str,
    username: str,
    hostname: str,
    servername: str,
    realname: str
) -> None:
    client.is_osu = (
        (realname == "osu" or realname.isdigit()) and
        hostname == "False" and
        servername == "*" and
        username == "OSU" and
        prefix == ""
    )

    if client.is_osu and not OSU_IRC_ENABLED:
        client.enqueue_banchobot_message("osu! IRC connections have been disabled. Please check back later!")
        client.close_connection("osu! IRC is disabled")
        return

@register("PASS")
@ensure_unauthenticated
def handle_pass_command(
    client: IrcClient,
    prefix: str,
    token: str
) -> None:
    client.token = token

    if client.name != "":
        client.on_login_received()

@register("NICK")
@ensure_unauthenticated
def handle_nick_command(
    client: IrcClient,
    prefix: str,
    nickname: str
) -> None:
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
