
from typing import Callable, List, Tuple, Iterator
from sqlalchemy.orm import selectinload, Session
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

@register(PacketType.OsuErrorReport)
def bancho_error(client: OsuClient, error: str):
    session.logger.warning(f'Bancho Error Report:\n{error}')

@register(PacketType.OsuChangeFriendOnlyDms)
def change_friendonly_dms(client: OsuClient, enabled: bool):
    client.info.friendonly_dms = enabled

@register(PacketType.OsuBeatmapInfoRequest)
def beatmap_info(client: OsuClient, info: BeatmapInfoRequest):
    total_maps = len(info.ids) + len(info.filenames)

    if total_maps <= 0:
        return

    client.logger.info(f'Got {total_maps} beatmap requests')

    # Limit request filenames/ids
    info.ids = info.ids[:4500]
    info.filenames = info.filenames[:4500]

    filenames_chunks = [
        info.filenames[i:i + 100]
        for i in range(0, len(info.filenames), 100)
    ]
    ids_chunks = [
        info.ids[i:i + 100]
        for i in range(0, len(info.ids), 100)
    ]

    session.tasks.do_later(
        process_beatmap_info_request,
        client,
        filenames_chunks,
        ids_chunks,
        priority=5
    )

def process_beatmap_info_request(
    client: OsuClient,
    filenames_chunks: List[List[str]],
    ids_chunks: List[List[int]]
) -> None:
    reply = BeatmapInfoReply()

    for index, filenames in enumerate(filenames_chunks):
        maps = process_filename_chunk(
            client, filenames,
            index * len(filenames)
        )
        reply.beatmaps.extend(maps)

    for index, ids in enumerate(ids_chunks):
        maps = process_id_chunk(
            client,
            ids
        )
        reply.beatmaps.extend(maps)

    client.logger.info(f'Sending reply with {len(reply.beatmaps)} beatmaps')
    client.enqueue_packet(PacketType.BanchoBeatmapInfoReply, reply)

def process_filename_chunk(
    client: OsuClient,
    filenames: List[str],
    index_offset: int = 0
) -> Iterator[BeatmapInfo]:
    maps: List[Tuple[int, DBBeatmap]] = []

    # Fetch all matching beatmaps from database
    with session.database.managed_session() as database_session:
        filename_beatmaps = database_session.query(DBBeatmap) \
            .options(selectinload(DBBeatmap.beatmapset)) \
            .filter(DBBeatmap.filename.in_(filenames)) \
            .all()

        found_beatmaps = {
            beatmap.filename: beatmap
            for beatmap in filename_beatmaps
        }

        for index, filename in enumerate(filenames):
            if filename not in found_beatmaps:
                continue

            # The client will identify the beatmaps by their index
            # in the "beatmapInfoSendList" array for the filenames
            maps.append((
                index_offset + index,
                found_beatmaps[filename]
            ))

        # Create the beatmap info response
        return create_beatmap_info_response(client, maps, database_session)

def process_id_chunk(client: OsuClient, ids: List[int]) -> Iterator[BeatmapInfo]:
    maps: List[Tuple[int, DBBeatmap]] = []

    # Fetch all matching beatmaps from database
    with session.database.managed_session() as database_session:
        id_beatmaps = database_session.query(DBBeatmap) \
            .options(selectinload(DBBeatmap.beatmapset)) \
            .filter(DBBeatmap.id.in_(ids)) \
            .all()

        for beatmap in id_beatmaps:
            # For the ids, the client doesn't require the index
            # and we can just set it to -1, so that it will lookup
            # the beatmap by its id
            maps.append((
                -1,
                beatmap
            ))

        # Create the beatmap info response
        return create_beatmap_info_response(client, maps, database_session)

def create_beatmap_info_response(
    client: OsuClient,
    maps: List[Tuple[int, DBBeatmap]],
    database_session: Session
) -> Iterator[BeatmapInfo]:
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
            grade = database_session.query(DBScore.grade) \
                .filter(DBScore.beatmap_id == beatmap.id) \
                .filter(DBScore.user_id == client.id) \
                .filter(DBScore.mode == mode) \
                .filter(DBScore.status_score == 3) \
                .filter(DBScore.hidden == False) \
                .scalar()

            if grade:
                grades[mode] = Rank[grade]

        yield BeatmapInfo(
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
