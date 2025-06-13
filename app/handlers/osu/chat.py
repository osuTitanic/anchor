
from app.common.database.repositories import wrapper, messages
from app.objects.channel import Channel
from app.clients.osu import OsuClient
from app.common import officer
from app import session

from chio import PacketType, Message
from typing import Callable
from time import time

def register(packet: PacketType) -> Callable:
    def wrapper(func) -> Callable:
        session.osu_handlers[packet] = func
        return func
    return wrapper

@wrapper.exception_wrapper()
def resolve_channel(channel_name: str, client: OsuClient) -> Channel | None:
    if channel_name == '#spectator':
        # Select spectator chat
        return (
            client.spectating.spectator_chat
            if client.spectating else
               client.spectator_chat
        )

    elif channel_name == '#multiplayer':
        # Select multiplayer chat
        return client.match.chat

    # Resolve channel by name
    if channel := session.channels.by_name(channel_name):
        return channel

@register(PacketType.OsuChannelJoin)
def handle_channel_join(client: OsuClient, channel_name: str):
    client_channels = (
        '#userlog',
        '#highlight'
    )

    if channel_name in client_channels:
        client.enqueue_channel_join_success(channel_name)
        return

    if not (channel := resolve_channel(channel_name, client)):
        client.enqueue_channel_revoked(channel_name)
        return

    channel.add(client)

@register(PacketType.OsuChannelLeave)
def channel_leave(client: OsuClient, channel_name: str, kick: bool = False):
    if not (channel := resolve_channel(channel_name, client)):
        client.enqueue_channel_revoked(channel_name)
        return

    if kick:
        client.enqueue_channel_revoked(channel_name)

    channel.remove(client)

@register(PacketType.OsuMessage)
def send_message(client: OsuClient, message: Message):
    client_channels = (
        '#userlog',
        '#highlight'
    )

    if message.target in client_channels:
        return

    if not (channel := resolve_channel(message.target, client)):
        client.enqueue_channel_revoked(message.target)
        return

    if message.content.startswith('/me'):
        message.content = f'\x01ACTION{message.content.removeprefix("/me")}\x01'

    if not client.is_bot and not client.message_limiter.allow():
        return client.silence(60, 'Chat spamming')

    channel.send_message(client, message.content.strip())

@register(PacketType.OsuPrivateMessage)
def send_private_message(sender: OsuClient, message: Message):
    if message.target == 'peppy':
        # This could be an internal osu! anti-cheat message
        officer.call(f'{sender.name} tried to message peppy: "{message.content}"')
        return

    if not (target := session.players.by_name(message.target)):
        sender.enqueue_channel_revoked(message.target)
        return

    if target.id == sender.id:
        return

    if sender.silenced:
        sender.logger.warning(
            'Failed to send private message: Sender was silenced'
        )
        return

    if target.silenced:
        sender.enqueue_packet(PacketType.BanchoTargetIsSilenced, target.name)
        return

    if target.friendonly_dms and sender.id not in target.friends:
        sender.enqueue_packet(PacketType.BanchoUserDmsBlocked, target.name)
        return

    if not sender.is_bot and not sender.message_limiter.allow():
        return sender.silence(60, 'Chat spamming')

    parsed_message = message.content.strip()
    has_command_prefix = parsed_message.startswith('!')

    if has_command_prefix or target is session.banchobot:
        return session.tasks.do_later(
            session.banchobot.process_and_send_response,
            parsed_message, sender, target, priority=1
        )

    if len(message.content) > 512:
        # Limit message size
        message.content = message.content[:497] + '... (truncated)'

    if target.away_message:
        return sender.enqueue_away_message(target)

    target.enqueue_message(
        message.content,
        sender,
        sender.name
    )

    session.tasks.do_later(
        messages.create_private,
        sender.id,
        target.id,
        message.content[:512],
        priority=3
    )

    sender.logger.info(
        f'[PM -> {target.name}]: {message.content}'
    )

@register(PacketType.OsuSetIrcAwayMessage)
def away_message(client: OsuClient, message: Message):
    if client.away_message is None and message.content == "":
        return

    if message.content != "":
        client.logger.info(f'Player was marked as being away: {message.content}')
        client.away_message = message.content
        client.enqueue_message(
            f'You have been marked as away: {message.content}',
            session.banchobot,
            session.banchobot.name
        )
        return

    client.logger.info('Player is no longer marked as being away.')
    client.away_message = None
    client.enqueue_message(
        'You are no longer marked as being away',
        session.banchobot,
        session.banchobot.name
    )
