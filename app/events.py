
from app.common.database.repositories import users, messages
from app.common.constants import GameMode, UserActivity
from app.common.config import config_instance as config
from app.common.helpers import infringements, activity
from app.common.database.objects import DBActivity
from app.clients.base import Client
from app.common import officer
from datetime import datetime
from typing import Optional

import json
import app
import sys

@app.session.events.register('bot_message')
def bot_message(message: str, target: str):
    if not (channel := app.session.channels.by_name(target)):
        return

    messages = message.split('\n')

    for message in messages:
        channel.send_message(
            app.session.banchobot,
            message,
            ignore_commands=True
        )

@app.session.events.register('bancho_event')
def bancho_event(
    user_id: int,
    mode: int,
    type: int,
    data: dict,
    is_announcement: bool = False
) -> None:
    if not is_announcement:
        return

    # Create entry object for formatting
    entry = DBActivity(
        user_id=user_id,
        mode=mode,
        type=type,
        data=data
    )

    send_activity_announcement(entry)
    send_activity_webhook(entry)

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

    if mode is not None:
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
    message: str,
    submit_to_webhook: bool = True
) -> None:
    if not (channel := app.session.channels.by_name(target)):
        return

    messages = message.split('\n')

    for message in messages:
        channel.handle_external_message(
            message,
            sender,
            sender_id,
            submit_to_webhook
        )

@app.session.events.register('external_dm')
def external_dm(
    sender_id: int,
    target_id: int,
    message: str,
    message_id: int
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

    # We assume the message will be read
    # This is to ensure the user won't recieve
    # unnecessary notifications for unread messages
    messages.update_private(
        message_id,
        {'read': True}
    )

@app.session.events.register('shutdown')
def shutdown() -> None:
    sys.exit(0)

def send_activity_announcement(entry: DBActivity) -> None:
    formatter = activity.text_formatters.get(entry.type)

    if not formatter:
        return

    if not (message := formatter(entry)):
        return

    # Send message in #announce channel
    bot_message(message, "#announce")

def send_activity_webhook(entry: DBActivity) -> None:
    formatter = activity.discord_formatters.get(entry.type)

    if not formatter:
        return

    if not (embed := formatter(entry)):
        return

    webhook_url_mapping = {
        UserActivity.BeatmapLeaderboardRank.value: config.ANNOUNCE_EVENTS_WEBHOOK_URL,
        UserActivity.RanksGained.value: config.ANNOUNCE_EVENTS_WEBHOOK_URL,
        UserActivity.NumberOne.value: config.ANNOUNCE_EVENTS_WEBHOOK_URL,
        UserActivity.PPRecord.value: config.ANNOUNCE_EVENTS_WEBHOOK_URL,
        UserActivity.BeatmapUploaded.value: config.BEATMAP_EVENTS_WEBHOOK_URL,
        UserActivity.BeatmapRevived.value: config.BEATMAP_EVENTS_WEBHOOK_URL,
        UserActivity.BeatmapStatusUpdated.value: config.BEATMAP_EVENTS_WEBHOOK_URL,
        UserActivity.BeatmapNominated.value: config.BEATMAP_EVENTS_WEBHOOK_URL,
        UserActivity.BeatmapNuked.value: config.BEATMAP_EVENTS_WEBHOOK_URL,
        UserActivity.ForumTopicCreated.value: config.FORUM_EVENTS_WEBHOOK_URL,
        UserActivity.ForumPostCreated.value: config.FORUM_EVENTS_WEBHOOK_URL
    }
    webhook_url = webhook_url_mapping.get(
        entry.type,
        config.ANNOUNCE_EVENTS_WEBHOOK_URL
    )

    # Send webhook message
    officer.event(
        embeds=[embed],
        url=webhook_url
    )

def enqueue_stats(player: Client):
    try:
        player.status.update_stats = True
        app.session.players.send_stats(player)
    finally:
        player.status.update_stats = False
