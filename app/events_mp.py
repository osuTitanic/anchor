
from chio import Mods, ScoringType, SlotTeam, TeamType
from twisted.internet import reactor
from collections.abc import Callable
from typing import Any, TypeVar
from enum import StrEnum

from app.common.constants import GameMode
from app.objects.multiplayer import Match

import app


class MultiplayerEventType(StrEnum):
    Start = "start"
    CancelStart = "cancel_start"
    Countdown = "countdown"
    CancelCountdown = "cancel_countdown"
    Close = "close"
    Abort = "abort"
    SetBeatmap = "set_beatmap"
    SetMods = "set_mods"
    SetFreemod = "set_freemod"
    SetHost = "set_host"
    ClearHost = "clear_host"
    InvitePlayer = "invite_player"
    ForceInvitePlayer = "force_invite_player"
    LockSlots = "lock_slots"
    UnlockSlots = "unlock_slots"
    KickPlayer = "kick_player"
    BanPlayer = "ban_player"
    UnbanPlayer = "unban_player"
    SetName = "set_name"
    SetSettings = "set_settings"
    SetSlotSize = "set_slot_size"
    MovePlayer = "move_player"
    SetTeam = "set_team"
    SetPassword = "set_password"
    AddReferee = "add_referee"
    RemoveReferee = "remove_referee"

class MultiplayerEventError(ValueError):
    pass

EventData = dict[str, Any]
EventHandler = Callable[[Match, EventData], None]
EnumType = TypeVar("EnumType")


@app.session.events.register("multiplayer")
def multiplayer_event(
    match_id: int,
    event_type: str,
    data: EventData | None = None
) -> None:
    try:
        resolved_type = MultiplayerEventType(event_type)
    except (TypeError, ValueError):
        app.session.logger.warning(f"Rejected multiplayer event: unknown event type {event_type!r}")
        return

    if data is None:
        data = {}

    match = next(
        (
            active_match
            for active_match in app.session.matches.active
            if active_match.db_match is not None
            and active_match.db_match.id == match_id
        ),
        None,
    )

    if match is None:
        app.session.logger.warning(
            f"Rejected multiplayer event {resolved_type.value!r}: "
            f"match {match_id} is not active"
        )
        return

    try:
        event_handlers[resolved_type](match, data)
    except MultiplayerEventError as error:
        match.logger.warning(f"Rejected '{resolved_type.value}' event: {error}")
        return
    except Exception:
        match.logger.exception(f"Failed to process '{resolved_type.value}' event")
        return

    match.logger.info(f"Processed '{resolved_type.value}' event")

def start(match: Match, data: EventData) -> None:
    duration = optional_int(data, "duration", minimum=0, maximum=60 * 5)
    force = optional_bool(data, "force", False)

    if match.in_progress:
        raise MultiplayerEventError("match is already running")

    if duration is not None:
        match.create_start_timer(duration, override=False)
        return

    if not match.player_slots:
        raise MultiplayerEventError("match has no players")

    if force:
        match.start()
        return

    result, remaining = match.start_safe()

    if result == "start_timer":
        raise MultiplayerEventError(f"match is already starting in {remaining} seconds")
    if result == "no_players":
        raise MultiplayerEventError("match has no players")
    if result == "not_ready":
        raise MultiplayerEventError("not all players are ready")

def cancel_start(match: Match, data: EventData) -> None:
    if not match.abort_start_timer():
        raise MultiplayerEventError("start timer is not active")

def countdown(match: Match, data: EventData) -> None:
    duration = require_int(data, "duration", minimum=0, maximum=60 * 15)
    match.create_countdown(duration, override=False)

def cancel_countdown(match: Match, data: EventData) -> None:
    if not match.abort_countdown():
        raise MultiplayerEventError("countdown is not active")

def close(match: Match, data: EventData) -> None:
    match.close()

def abort(match: Match, data: EventData) -> None:
    if not match.in_progress:
        raise MultiplayerEventError("match is not running")

    match.abort()

def set_beatmap(match: Match, data: EventData) -> None:
    beatmap_id = require_int(data, "beatmap_id", minimum=1)
    mode_value = optional_int(data, "mode", minimum=0, maximum=3)
    mode = GameMode(mode_value) if mode_value is not None else None

    if match.set_beatmap(beatmap_id, mode) is None:
        raise MultiplayerEventError(f"beatmap {beatmap_id} was not found")

def set_mods(match: Match, data: EventData) -> None:
    mods_value = require_int(data, "mods", minimum=0, maximum=0xFFFFFFFF)
    freemod = optional_bool(data, "freemod", match.freemod)

    try:
        mods = Mods(mods_value)
    except ValueError as error:
        raise MultiplayerEventError(f"invalid mods value {mods_value}") from error

    match.set_mods(mods, freemod)

def set_freemod(match: Match, data: EventData) -> None:
    freemod = require_bool(data, "enabled")
    match.set_mods(match.mods, freemod)

def set_host(match: Match, data: EventData) -> None:
    target = require_match_player(match, data)
    match.set_host(target)

def clear_host(match: Match, data: EventData) -> None:
    if not match.clear_host():
        raise MultiplayerEventError("match has no host")

def invite_player(match: Match, data: EventData) -> None:
    target = require_player(data)
    match.invite_player(target)

def force_invite_player(match: Match, data: EventData) -> None:
    target = require_player(data)
    match.invite_player(target, force=True)

def lock_slots(match: Match, data: EventData) -> None:
    match.lock_slots()

def unlock_slots(match: Match, data: EventData) -> None:
    match.unlock_slots()

def kick_player(match: Match, data: EventData) -> None:
    target = require_match_player(match, data)
    match.kick_player(target)

def ban_player(match: Match, data: EventData) -> None:
    target = require_player(data)
    match.ban_player(target)

def unban_player(match: Match, data: EventData) -> None:
    target = require_player(data)

    if target.id not in match.banned_players:
        raise MultiplayerEventError(f"player {target.id} is not banned")

    match.unban_player(target)

def set_name(match: Match, data: EventData) -> None:
    match.set_name(require_string(data, "name", allow_empty=False))

def set_settings(match: Match, data: EventData) -> None:
    team_type = require_enum(TeamType, data, "team_type")
    scoring_type = optional_enum(ScoringType, data, "scoring_type")
    slot_size = optional_int(data, "slot_size", minimum=1, maximum=len(match.slots))

    match.set_team_type(
        team_type,
        update=False
    )

    if scoring_type is not None:
        match.set_scoring_type(scoring_type, update=False)

    if slot_size is not None:
        match.set_slot_size(slot_size, update=False)

    if not match.close_if_empty():
        match.update()

def set_slot_size(match: Match, data: EventData) -> None:
    size = require_int(data, "slot_size", minimum=1, maximum=len(match.slots))
    match.set_slot_size(size)

def move_player(match: Match, data: EventData) -> None:
    target = require_match_player(match, data)
    slot_id = require_int(data, "slot_id", minimum=1, maximum=len(match.slots))

    if not match.move_player(target, slot_id):
        raise MultiplayerEventError(f"player {target.id} could not be moved")

def set_team(match: Match, data: EventData) -> None:
    target = require_match_player(match, data)
    team = require_enum(SlotTeam, data, "team")

    if not match.set_team(target, team):
        raise MultiplayerEventError(f"player {target.id} is not in the match")

def set_password(match: Match, data: EventData) -> None:
    match.set_password(require_string(data, "password"))

def add_referee(match: Match, data: EventData) -> None:
    target = require_user(data)

    if not match.add_referee(target):
        raise MultiplayerEventError(f"player {target.id} is already a referee")

def remove_referee(match: Match, data: EventData) -> None:
    target = require_user(data)

    if not match.remove_referee(target):
        raise MultiplayerEventError(f"player {target.id} is not a referee")


def require_user(data: EventData):
    user_id = require_int(data, "user_id", minimum=1)
    resolved_player = app.session.players.by_id(user_id)

    if resolved_player is None:
        raise MultiplayerEventError(f"user {user_id} is not online")

    return resolved_player

def require_player(data: EventData):
    player_id = require_int(data, "user_id", minimum=1)
    resolved_player = app.session.players.by_id_osu(player_id)

    if resolved_player is None:
        raise MultiplayerEventError(f"osu! player {player_id} is not online")

    return resolved_player

def require_match_player(match: Match, data: EventData):
    player = require_player(data)

    if player not in match.players:
        raise MultiplayerEventError(f"player {player.id} is not in the match")

    return player

def require_int(
    data: EventData,
    key: str,
    minimum: int | None = None,
    maximum: int | None = None
) -> int:
    value = data.get(key)

    if isinstance(value, bool) or not isinstance(value, int):
        raise MultiplayerEventError(f"{key} must be an integer")
    if minimum is not None and value < minimum:
        raise MultiplayerEventError(f"{key} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise MultiplayerEventError(f"{key} must be at most {maximum}")

    return value

def optional_int(
    data: EventData,
    key: str,
    minimum: int | None = None,
    maximum: int | None = None
) -> int | None:
    if key not in data:
        return None

    return require_int(data, key, minimum, maximum)

def require_bool(data: EventData, key: str) -> bool:
    value = data.get(key)

    if not isinstance(value, bool):
        raise MultiplayerEventError(f"{key} must be a boolean")

    return value

def optional_bool(data: EventData, key: str, default: bool) -> bool:
    if key not in data:
        return default

    return require_bool(data, key)

def require_string(data: EventData, key: str, allow_empty: bool = True) -> str:
    value = data.get(key)

    if not isinstance(value, str):
        raise MultiplayerEventError(f"{key} must be a string")
    if not allow_empty and not value.strip():
        raise MultiplayerEventError(f"{key} cannot be empty")

    return value

def require_enum(
    enum_type: Callable[[int], EnumType],
    data: EventData,
    key: str
) -> EnumType:
    value = require_int(data, key)

    try:
        return enum_type(value)
    except ValueError as error:
        raise MultiplayerEventError(f"invalid {key} value {value}") from error

def optional_enum(
    enum_type: Callable[[int], EnumType],
    data: EventData,
    key: str
) -> EnumType | None:
    if key not in data:
        return None

    return require_enum(enum_type, data, key)


event_handlers: dict[MultiplayerEventType, EventHandler] = {
    MultiplayerEventType.Start: start,
    MultiplayerEventType.CancelStart: cancel_start,
    MultiplayerEventType.Countdown: countdown,
    MultiplayerEventType.CancelCountdown: cancel_countdown,
    MultiplayerEventType.Close: close,
    MultiplayerEventType.Abort: abort,
    MultiplayerEventType.SetBeatmap: set_beatmap,
    MultiplayerEventType.SetMods: set_mods,
    MultiplayerEventType.SetFreemod: set_freemod,
    MultiplayerEventType.SetHost: set_host,
    MultiplayerEventType.ClearHost: clear_host,
    MultiplayerEventType.InvitePlayer: invite_player,
    MultiplayerEventType.ForceInvitePlayer: force_invite_player,
    MultiplayerEventType.LockSlots: lock_slots,
    MultiplayerEventType.UnlockSlots: unlock_slots,
    MultiplayerEventType.KickPlayer: kick_player,
    MultiplayerEventType.BanPlayer: ban_player,
    MultiplayerEventType.UnbanPlayer: unban_player,
    MultiplayerEventType.SetName: set_name,
    MultiplayerEventType.SetSettings: set_settings,
    MultiplayerEventType.SetSlotSize: set_slot_size,
    MultiplayerEventType.MovePlayer: move_player,
    MultiplayerEventType.SetTeam: set_team,
    MultiplayerEventType.SetPassword: set_password,
    MultiplayerEventType.AddReferee: add_referee,
    MultiplayerEventType.RemoveReferee: remove_referee,
}
