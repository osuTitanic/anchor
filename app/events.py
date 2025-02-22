
from __future__ import annotations

from app.objects.player import Player
from app.common import officer
from app.common.objects import bMessage
from app.common.constants import GameMode
from app.common.cache import leaderboards
from app.common.database.repositories import (
    infringements,
    clients,
    scores,
    groups,
    stats,
    users
)

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
            message,
            ignore_privs=True
        )

@app.session.events.register('logout')
def logout(user_id: int):
    if not (player := app.session.players.by_id(user_id)):
        return

    player.close_connection()

@app.session.events.register('restrict')
def restrict(
    user_id: int,
    reason: str = '',
    autoban: bool = False,
    until: Optional[datetime] = None
) -> None:
    if not (player := app.session.players.by_id(user_id)):
        # Player is not online
        player = users.fetch_by_id(user_id)

        if not player:
            # Player was not found
            officer.call(f'Failed to restrict user with id {user_id}: User not found!')
            return

        # Update user
        users.update(player.id, {'restricted': True})

        # Remove permissions
        groups.delete_entry(player.id, 999)
        groups.delete_entry(player.id, 1000)

        leaderboards.remove(
            player.id,
            player.country
        )

        # Hide scores
        scores.hide_all(player.id)
        stats.update_all(player.id, {'rank': 0})

        # Update hardware
        clients.update_all(player.id, {'banned': True})

        # Add entry inside infringements table
        infringements.create(
            player.id,
            action=0,
            length=until,
            description=reason,
            is_permanent=True if not until else False
        )

        officer.call(
            f'{player.name} was {"auto-" if autoban else ""}restricted. Reason: "{reason}"'
        )
        return

    player.restrict(reason, until, autoban)

@app.session.events.register('silence')
def silence(user_id: int, duration: int, reason: str = ''):
    if not (player := app.session.players.by_id(user_id)):
        return

    player.silence(duration, reason)

@app.session.events.register('unrestrict')
def unrestrict(user_id: int, restore_scores: bool = True):
    if not (player := users.fetch_by_id(user_id)):
        return

    if not player.restricted:
        return

    users.update(player.id, {'restricted': False})

    # Add to player & supporter group
    groups.create_entry(player.id, 999)
    groups.create_entry(player.id, 1000)

    # Update hardware
    clients.update_all(player.id, {'banned': False})

    if restore_scores:
        scores.restore_hidden_scores(player.id)
    else:
        stats.delete_all(player.id)
        leaderboards.remove(player.id, player.country)

    for user_stats in stats.fetch_all(player.id):
        leaderboards.update(
            user_stats,
            player.country
        )

    officer.call(f'Player "{player.name}" was unrestricted.')

@app.session.events.register('announcement')
def announcement(message: str):
    app.session.logger.info(f'Announcement: "{message}"')
    app.session.players.announce(message)

@app.session.events.register('user_announcement')
def user_announcement(user_id: int, message: str):
    if not (player := app.session.players.by_id(user_id)):
        return

    player.enqueue_announcement(message)

@app.session.events.register('user_update')
def user_update(user_id: int, mode: int | None = None):
    if not (player := app.session.players.by_id(user_id)):
        return

    if mode != None:
        # Assign new mode to the player
        player.status.mode = GameMode(mode)

    player.reload_object()
    enqueue_stats(player)

    duplicates = app.session.players.get_rank_duplicates(
        player.rank,
        player.status.mode
    )

    for p in duplicates:
        if p.id == player.id:
            continue

        # We have found a player with the same rank
        player.reload_object()
        enqueue_stats(player)

@app.session.events.register('link')
def link_discord_user(user_id: int, code: str):
    if not (player := app.session.players.by_id(user_id)):
        app.session.logger.warning('Failed to link user to discord: Not Online!')
        return

    if player.object.discord_id:
        app.session.logger.warning('Failed to link user to discord: Already Linked!')
        return

    player.enqueue_message(
        bMessage(
            app.session.banchobot.name,
            f'Your verification code is: "{code}". Please type it into discord to link your account!',
            player.name,
            sender_id=app.session.banchobot.id,
            is_private=True
        )
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
        msg := bMessage(
            sender.name,
            message,
            target.name,
            sender_id=sender.id,
            is_private=True
        )
    )

    if (online_sender := app.session.players.by_id(sender_id)):
        online_sender.enqueue_message(msg)

@app.session.events.register('shutdown')
def shutdown():
    """Used to shutdown the event_listener thread"""
    exit()

def enqueue_stats(player: Player):
    for p in app.session.players:
        if p.client.version.date > 20121223 and p.id != player.id:
            # Client will request the stats
            # themselves when pressing F9
            continue

        if p.client.version.date <= 377:
            # Client needs the "update" flag to
            # be set for the stats to be updated
            p.enqueue_presence(player, update=True)
            continue

        p.enqueue_stats(player)
