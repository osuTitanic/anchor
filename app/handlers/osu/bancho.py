
from chio import PacketType, BeatmapInfoReply, BeatmapInfoRequest, BeatmapInfo, Rank
from typing import Callable, List, Tuple
from sqlalchemy.orm import selectinload

from app.common.database.objects import DBBeatmap, DBScore
from app.clients.osu import OsuClient
from app import session

def register(packet: PacketType) -> Callable:
    def wrapper(func) -> Callable:
        session.handlers[packet] = func
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
def beatmap_info(client: OsuClient, info: BeatmapInfoRequest, ignore_limit: bool = False):
    maps: List[Tuple[int, DBBeatmap]] = []

    # Limit request filenames/ids
    if not ignore_limit:
        info.beatmap_ids = info.beatmap_ids[:100]
        info.filenames = info.filenames[:100]

    total_maps = len(info.beatmap_ids) + len(info.filenames)

    if total_maps <= 0:
        return

    client.logger.info(f'Got {total_maps} beatmap requests')

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
            .filter(DBBeatmap.id.in_(info.beatmap_ids)) \
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

            ranked = {
                -3: -1, # Not submitted
                -2: 0,  # Graveyard: Pending
                -1: 0,  # WIP: Pending
                 0: 0,  # Pending: Pending
                 1: 1,  # Ranked: Ranked
                 2: 2,  # Approved: Approved
                 3: 2,  # Qualified: Approved
                 4: 2,  # Loved: Approved
            }[beatmap.status]

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
                    ranked,
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
    client.client.friendonly_dms = enabled
