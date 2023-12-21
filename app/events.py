
from app.common.cache import leaderboards
from app.common.database.repositories import (
    infringements,
    clients,
    scores,
    stats,
    users
)

from datetime import datetime
from typing import Optional

import config
import json
import app

@app.session.events.register('user_update')
def user_update(user_id: int):
    if not (player := app.session.players.by_id(user_id)):
        return

    player.reload_object()

    duplicates = app.session.players.get_rank_duplicates(
        player.rank,
        player.status.mode
    )

    for p in duplicates:
        if p.id == player.id:
            continue

        # We have found a player with the same rank
        player.reload_object()

        for p in app.session.players:
            if p.client.version.date <= 377:
                p.enqueue_presence(player, update=True)
                continue

            p.enqueue_stats(player)

    for p in app.session.players:
        if p.client.version.date <= 377:
            p.enqueue_presence(player, update=True)
            continue

        p.enqueue_stats(player)

@app.session.events.register('bot_message')
def bot_message(message: str, target: str):
    if not (channel := app.session.channels.by_name(target)):
        return

    messages = message.split('\n')

    for message in messages:
        channel.send_message(
            app.session.bot_player,
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
            app.session.logger.warning('Failed to restrict user: User not found!')
            return

        # Update user
        users.update(player.id,
            {
                'restricted': True,
                'permissions': 0
            }
        )

        leaderboards.remove(
            player.id,
            player.country
        )

        stats.delete_all(player.id)
        scores.hide_all(player.id)

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

        app.session.logger.warning(
            f'{player.name} got {"auto-" if autoban else ""}restricted. Reason: {reason}'
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

    users.update(player.id,
        {
            'restricted': False,
            'permissions': 5
        }
    )

    # Update hardware
    clients.update_all(player.id, {'banned': False})

    if restore_scores:
        try:
            scores.restore_hidden_scores(player.id)
            stats.restore(player.id)
        except Exception as e:
            app.session.logger.error(
                f'Failed to restore scores of player "{player.name}": {e}',
                exc_info=e
            )

    app.session.logger.warning(f'Player "{player.name}" was unrestricted.')

@app.session.events.register('announcement')
def announcement(message: str):
    app.session.logger.info(f'Announcement: "{message}"')
    app.session.players.announce(message)

@app.session.events.register('osu_error')
def osu_error(user_id: int, error: dict):
    if not (player := app.session.players.by_id(user_id)):
        return

    app.session.logger.warning(
        f'Client error from "{player.name}":\n'
        f'{json.dumps(error, indent=4)}'
    )

    if channel := app.session.channels.by_name('#admin'):
        channel.send_message(
            app.session.bot_player,
            f'Client error from "{player.name}". Please check the logs!',
            ignore_privs=True
        )

    # When a beatmap fails to load inside a match, the player
    # gets forced to the menu screen. In this state, everything
    # is a little buggy, but aborting the match fixes pretty much everything.
    if player.match and player.match.in_progress:
        if not player.match.in_progress:
            return

        player.match.abort()
        player.match.chat.send_message(
            app.session.bot_player,
            f"Match was aborted, due to client error from {player.name}. "
            "Please try again!",
            ignore_privs=True
        )

@app.session.events.register('shutdown')
def shutdown():
    """Used to shutdown the event_listener thread"""
    exit()
