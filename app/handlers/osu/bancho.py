
from typing import Callable, List, Tuple
from sqlalchemy.orm import selectinload
from chio import (
    BeatmapInfoRequest,
    BeatmapInfoReply,
    RankedStatus,
    BeatmapInfo,
    PacketType,
    Rank
)

from app.common.database.objects import DBBeatmap, DBScore
from app.clients.osu import OsuClient
from app import session

def register(packet: PacketType) -> Callable:
    def wrapper(func) -> Callable:
        session.osu_handlers[packet] = func
        return func
    return wrapper

@register(PacketType.OsuPong)
def pong(client: OsuClient):
    pass # lol

@register(PacketType.OsuExit)
def exit(client: OsuClient, updating: bool):
    client.update_activity()
    client.close_connection()

@register(PacketType.OsuBeatmapInfoRequest)
def beatmap_info(client: OsuClient, info: BeatmapInfoRequest):
    maps: List[Tuple[int, DBBeatmap]] = []
    total_maps = len(info.ids) + len(info.filenames)

    if total_maps <= 0:
        return

    client.logger.info(f'Got {total_maps} beatmap requests')

    # Use a different limit if client is older than ~b830.
    # They seem to always request all maps at once, which
    # can cause the request size to be larger than usual.
    limit = 5000 if client.info.version.date <= 830 else 250

    # Limit request filenames/ids
    info.ids = info.ids[:limit]
    info.filenames = info.filenames[:limit]

    # Fetch all matching beatmaps from database
    with session.database.managed_session() as s:
        filename_beatmaps = s.query(DBBeatmap) \
            .options(selectinload(DBBeatmap.beatmapset)) \
            .filter(DBBeatmap.filename.in_(info.filenames)) \
            .all()

        found_beatmaps = {
            beatmap.filename:beatmap
            for beatmap in filename_beatmaps
        }

        for index, filename in enumerate(info.filenames):
            if filename not in found_beatmaps:
                continue

            # The client will identify the beatmaps by their index
            # in the "beatmapInfoSendList" array for the filenames
            maps.append((
                index,
                found_beatmaps[filename]
            ))

        id_beatmaps = s.query(DBBeatmap) \
            .options(selectinload(DBBeatmap.beatmapset)) \
            .filter(DBBeatmap.id.in_(info.ids)) \
            .all()

        for beatmap in id_beatmaps:
            # For the ids, the client doesn't require the index
            # and we can just set it to -1, so that it will lookup
            # the beatmap by its id
            maps.append((
                -1,
                beatmap
            ))

        # Create beatmap response
        map_infos: List[BeatmapInfo] = []

        for index, beatmap in maps:
            if beatmap.status <= -3:
                # Not submitted
                continue

            status_mapping = {
                -3: RankedStatus.NotSubmitted,
                -2: RankedStatus.Pending,
                -1: RankedStatus.Pending,
                 0: RankedStatus.Pending,
                 1: RankedStatus.Ranked,
                 2: RankedStatus.Approved,
                 3: RankedStatus.Qualified,
                 4: RankedStatus.Loved,
            }

            # Get personal best in every mode for this beatmap
            grades = {
                0: Rank.N,
                1: Rank.N,
                2: Rank.N,
                3: Rank.N
            }

            for mode in range(4):
                grade = s.query(DBScore.grade) \
                    .filter(DBScore.beatmap_id == beatmap.id) \
                    .filter(DBScore.user_id == client.id) \
                    .filter(DBScore.mode == mode) \
                    .filter(DBScore.status_score == 3) \
                    .filter(DBScore.hidden == False) \
                    .scalar()

                if grade:
                    grades[mode] = Rank[grade]

            map_infos.append(
                BeatmapInfo(
                    index,
                    beatmap.id,
                    beatmap.set_id,
                    beatmap.beatmapset.topic_id or 0,
                    status_mapping.get(beatmap.status, RankedStatus.NotSubmitted),
                    beatmap.md5,
                    grades[0], # Standard
                    grades[2], # Fruits
                    grades[1], # Taiko
                    grades[3], # Mania
                )
            )

        client.logger.info(
            f'Sending reply with {len(map_infos)} beatmaps'
        )

        client.enqueue_packet(
            PacketType.BanchoBeatmapInfoReply,
            BeatmapInfoReply(map_infos)
        )

@register(PacketType.OsuErrorReport)
def bancho_error(client: OsuClient, error: str):
    session.logger.warning(f'Bancho Error Report:\n{error}')

@register(PacketType.OsuChangeFriendOnlyDms)
def change_friendonly_dms(client: OsuClient, enabled: bool):
    client.info.friendonly_dms = enabled
