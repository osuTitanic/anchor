
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
        hostname == "False" and
        servername == "*" and
        username == "OSU" and
        realname == "osu" and
        prefix == ""
    )

    if client.token != "" and client.name != "":
        client.on_login_received()

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
        # TODO: Handle osu! login via. chat

    if client.token != "":
        client.on_login_received()
