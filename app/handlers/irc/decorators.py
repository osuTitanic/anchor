
from typing import Callable
from app.clients.irc import IrcClient
from app import session

__all__ = [
    "register",
    "ensure_authenticated",
    "ensure_unauthenticated"
]

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

def ensure_unauthenticated(func: Callable) -> Callable:
    def wrapper(client: IrcClient, *args, **kwargs) -> None:
        if client.logged_in:
            return
        return func(client, *args, **kwargs)
    return wrapper
