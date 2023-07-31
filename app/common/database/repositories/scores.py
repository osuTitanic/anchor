
from app.common.database.objects import (
    DBBeatmap,
    DBScore,
    DBUser
)

from typing import Optional, List
from sqlalchemy import or_, func

import app

def create(score: DBScore) -> DBScore:
    with app.session.database.session as session:
        session.add(score)
        session.commit()

    return score

def fetch_by_id(id: int) -> Optional[DBScore]:
    return app.session.database.temp_session.query(DBScore) \
        .filter(DBScore.id == id) \
        .first()

def fetch_by_replay_checksum(checksum: str) -> Optional[DBScore]:
    return app.session.database.temp_session.query(DBScore) \
            .filter(DBScore.replay_md5 == checksum) \
            .first()

def fetch_count(user_id: int, mode: int) -> int:
    return app.session.database.temp_session.query(DBScore) \
            .filter(DBScore.user_id == user_id) \
            .filter(DBScore.mode == mode) \
            .filter(DBScore.status == 3) \
            .count()

def fetch_top_scores(user_id: int, mode: int, exclude_approved: bool = False) -> List[DBScore]:
    query = app.session.database.temp_session.query(DBScore) \
            .filter(DBScore.user_id == user_id) \
            .filter(DBScore.mode == mode) \
            .filter(DBScore.status == 3)

    if exclude_approved:
        query = query.filter(DBBeatmap.status == 1) \
                     .join(DBScore.beatmap)

    return query.order_by(DBScore.pp.desc()) \
                .limit(100) \
                .offset(0) \
                .all()

def fetch_personal_best(
    beatmap_id: int,
    user_id: int,
    mode: int,
    mods: Optional[int] = None
) -> Optional[DBScore]:
    if mods == None:
        return app.session.database.temp_session.query(DBScore) \
            .filter(DBScore.beatmap_id == beatmap_id) \
            .filter(DBScore.user_id == user_id) \
            .filter(DBScore.mode == mode) \
            .filter(DBScore.status == 3) \
            .first()

    return app.session.database.temp_session.query(DBScore) \
            .filter(DBScore.beatmap_id == beatmap_id) \
            .filter(DBScore.user_id == user_id) \
            .filter(DBScore.mode == mode) \
            .filter(or_(DBScore.status == 3, DBScore.status == 4)) \
            .filter(DBScore.mods == mods) \
            .first()

def fetch_range_scores(
    beatmap_id: int,
    mode: int,
    offset: int = 0,
    limit: int = 5
) -> List[DBScore]:
    return app.session.database.temp_session.query(DBScore) \
        .filter(DBScore.beatmap_id == beatmap_id) \
        .filter(DBScore.mode == mode) \
        .filter(DBScore.status == 3) \
        .order_by(DBScore.total_score.desc()) \
        .offset(offset) \
        .limit(limit) \
        .all()

def fetch_range_scores_country(
    beatmap_id: int,
    mode: int,
    country: str,
    limit: int = 5
) -> List[DBScore]:
    return app.session.database.temp_session.query(DBScore) \
            .filter(DBScore.beatmap_id == beatmap_id) \
            .filter(DBScore.mode == mode) \
            .filter(DBScore.status == 3) \
            .filter(DBUser.country == country) \
            .join(DBScore.user) \
            .limit(limit) \
            .all()

def fetch_range_scores_friends(
    beatmap_id: int,
    mode: int,
    friends: List[int],
    limit: int = 5
) -> List[DBScore]:
    return app.session.database.temp_session.query(DBScore) \
            .filter(DBScore.beatmap_id == beatmap_id) \
            .filter(DBScore.mode == mode) \
            .filter(DBScore.status == 3) \
            .filter(DBScore.user_id.in_(friends)) \
            .limit(limit) \
            .all()

def fetch_range_scores_mods(
    beatmap_id: int,
    mode: int,
    mods: int,
    limit: int = 5
) -> List[DBScore]:
    return app.session.database.temp_session.query(DBScore) \
        .filter(DBScore.beatmap_id == beatmap_id) \
        .filter(DBScore.mode == mode) \
        .filter(or_(DBScore.status == 3, DBScore.status == 4)) \
        .filter(DBScore.mods == mods) \
        .order_by(DBScore.total_score.desc()) \
        .limit(limit) \
        .all()

def fetch_score_index(
    user_id: int,
    beatmap_id: int,
    mode: int,
    mods: Optional[int] = None,
    friends: Optional[List[int]] = None,
    country: Optional[str] = None
) -> int:
    with app.session.database.session as session:
        query = session.query(DBScore.user_id, DBScore.mods, func.rank() \
                    .over(
                        order_by=DBScore.total_score.desc()
                    ).label('rank')
                ) \
                .filter(DBScore.beatmap_id == beatmap_id) \
                .filter(DBScore.mode == mode) \
                .order_by(DBScore.total_score.desc())

        if mods != None:
            query = query.filter(DBScore.mods == mods) \
                         .filter(or_(DBScore.status == 3, DBScore.status == 4))

        if country != None:
            query = query.join(DBScore.user) \
                         .filter(DBScore.status == 3) \
                         .filter(DBUser.country == country) \

        if friends != None:
            query = query.filter(DBScore.status == 3) \
                         .filter(
                            or_(
                                DBScore.user_id.in_(friends),
                                DBScore.user_id == user_id
                            )
                         )

        subquery = query.subquery()

        if not (result := session.query(subquery.c.rank) \
                                 .filter(subquery.c.user_id == user_id) \
                                 .first()):
            return -1

        return result[-1]

def fetch_score_index_by_id(
    score_id: int,
    beatmap_id: int,
    mode: int,
    mods: Optional[int] = None
) -> int:
    with app.session.database.session as session:
        query = session.query(DBScore.id, DBScore.mods, func.rank() \
                    .over(
                        order_by=DBScore.total_score.desc()
                    ).label('rank')
                ) \
                .filter(DBScore.beatmap_id == beatmap_id) \
                .filter(DBScore.mode == mode) \
                .order_by(DBScore.total_score.desc())

        if mods != None:
            query = query.filter(DBScore.mods == mods) \
                         .filter(or_(DBScore.status == 3, DBScore.status == 4))
        else:
            query = query.filter(DBScore.status == 3)

        subquery = query.subquery()

        if not (result := session.query(subquery.c.rank) \
                                  .filter(subquery.c.id == score_id) \
                                  .first()):
            return -1

        return result[-1]

def fetch_score_above(
    beatmap_id: int,
    mode: int,
    total_score: int
) -> Optional[DBScore]:
    return app.session.database.temp_session.query(DBScore) \
            .filter(DBScore.beatmap_id == beatmap_id) \
            .filter(DBScore.mode == mode) \
            .filter(DBScore.total_score > total_score) \
            .filter(DBScore.status == 3) \
            .order_by(DBScore.total_score.asc()) \
            .first()

def fetch_recent(
    user_id: int,
    mode: int,
    limit: int = 3
) -> List[DBScore]:
    return app.session.database.temp_session.query(DBScore) \
                .filter(DBScore.user_id == user_id) \
                .filter(DBScore.mode == mode) \
                .order_by(DBScore.id.desc()) \
                .limit(limit) \
                .all()
