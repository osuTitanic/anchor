
from __future__ import annotations

from app.common.helpers import infringements, activity
from app.common.database.repositories import users
from app.common.database.objects import DBActivity
from app.common.constants import GameMode
from app.clients.base import Client
from datetime import datetime
from typing import Optional

import json
import app

@app.session.events.register('bot_message')
def bot_message(message: str, target: str):
    if not (channel := app.session.channels.by_name(target)):
        return

    messages = message.split('\n')

    for message in messages:
        channel.send_message(
            app.session.banchobot,
            message
        )

@app.session.events.register('bancho_event')
def bancho_event(user_id: int, mode: int, type: int, data: dict):
    # Create entry object for formatting
    entry = DBActivity(
        user_id=user_id,
        mode=mode,
        type=type,
        data=data
    )

    formatter = activity.formatters.get(type)

    if not formatter:
        app.session.logger.warning(f'No formatter found for activity type {type}')
        return

    # Send message in #announce channel
    bot_message(formatter(entry), "#announce")

@app.session.events.register('logout')
def logout(user_id: int):
    if not (player := app.session.players.by_id(user_id)):
        return

    player.close_connection("Kicked by logout event")

@app.session.events.register('restrict')
def restrict(
    user_id: int,
    reason: str = '',
    autoban: bool = False,
    until: Optional[datetime] = None
) -> None:
    if not (user := users.fetch_by_id(user_id)):
        return

    infringements.restrict_user(
        user,
        reason,
        until,
        autoban
    )

    if (player_osu := app.session.players.by_id_osu(user.id)):
        player_osu.on_user_restricted(reason, until, autoban)

    if (player_irc := app.session.players.by_id_irc(user.id)):
        player_irc.on_user_restricted(reason, until, autoban)

@app.session.events.register('unrestrict')
def unrestrict(user_id: int, restore_scores: bool = True):
    if not (user := users.fetch_by_id(user_id)):
        return

    if not user.restricted:
        return

    infringements.unrestrict_user(
        user,
        restore_scores
    )

    if (player_osu := app.session.players.by_id_osu(user.id)):
        player_osu.on_user_unrestricted()

    if (player_irc := app.session.players.by_id_irc(user.id)):
        player_irc.on_user_unrestricted()

@app.session.events.register('silence')
def silence(user_id: int, duration: int, reason: str = ''):
    if not (user := users.fetch_by_id(user_id)):
        return

    infringements.silence_user(
        user,
        duration,
        reason
    )

    if (player_osu := app.session.players.by_id_osu(user.id)):
        player_osu.on_user_silenced()

    if (player_irc := app.session.players.by_id_irc(user.id)):
        player_irc.on_user_silenced()

@app.session.events.register('update_user_silence')
def update_user_silence(user_id: int):
    if not (user := users.fetch_by_id(user_id)):
        return

    if (player_osu := app.session.players.by_id_osu(user.id)):
        player_osu.on_user_silenced()

    if (player_irc := app.session.players.by_id_irc(user.id)):
        player_irc.on_user_silenced()

@app.session.events.register('announcement')
def announcement(message: str):
    app.session.logger.info(f'Announcement: "{message}"')
    app.session.players.send_announcement(message)

@app.session.events.register('user_announcement')
def user_announcement(user_id: int, message: str):
    if not (player := app.session.players.by_id(user_id)):
        return

    player.enqueue_announcement(message)

@app.session.events.register('user_update')
def user_update(user_id: int, mode: int | None = None):
    if not (player := app.session.players.by_id(user_id)):
        return

    if player.is_irc and not player.is_osu:
        # User is not using an osu! client
        return

    if mode != None:
        # Assign new mode to the player
        player.status.mode = GameMode(mode)

    # Reload player data & distribute stats
    player.reload(player.status.mode.value)
    player.enqueue_stats(player)
    enqueue_stats(player)

    duplicates = app.session.players.by_rank(
        player.stats.rank,
        player.status.mode
    )

    for p in duplicates:
        if p.id == player.id:
            continue

        # We have found a player with the same rank
        p.reload(p.status.mode.value)
        p.enqueue_stats(p)
        enqueue_stats(p)

@app.session.events.register('link')
def link_discord_user(user_id: int, code: str):
    if not (player := app.session.players.by_id(user_id)):
        app.session.logger.warning('Failed to link user to discord: Not online!')
        return

    if player.object.discord_id:
        app.session.logger.warning('Failed to link user to discord: Already linked!')
        return

    player.enqueue_message(
        f'Your verification code is: "{code}". Please type it into discord to link your account!',
        app.session.banchobot,
        player.name
    )

@app.session.events.register('external_message')
def external_message(
    sender_id: int,
    sender: str,
    target: str,
    message: str
) -> None:
    if not (channel := app.session.channels.by_name(target)):
        return

    messages = message.split('\n')

    for message in messages:
        channel.handle_external_message(
            message,
            sender,
            sender_id
        )

@app.session.events.register('external_dm')
def external_dm(
    sender_id: int,
    target_id: int,
    message: str
) -> None:
    if not (target := app.session.players.by_id(target_id)):
        return

    if not (sender := users.fetch_by_id(sender_id)):
        return

    target.logger.info(
        f'(external) [{sender.name} -> {target.name}]: {message}'
    )

    target.enqueue_message(
        message, sender, target.name
    )

    if (online_sender := app.session.players.by_id(sender_id)):
        online_sender.enqueue_message(message, sender, target.name)

@app.session.events.register('shutdown')
def shutdown() -> None:
    exit(0)

def enqueue_stats(player: Client):
    try:
        player.status.update_stats = True
        app.session.players.send_stats(player)
    finally:
        player.status.update_stats = False
