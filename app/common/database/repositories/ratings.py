
from app.common.database import DBRating
from app.session import database

from typing import List, Optional
from sqlalchemy import func

def create(
    beatmap_hash: str,
    user_id: int,
    set_id: int,
    rating: int
) -> DBRating:
    with database.session as session:
        session.add(
            rating := DBRating(
                user_id,
                set_id,
                beatmap_hash,
                rating
            )
        )
        session.commit()

    return rating

def fetch_one(beatmap_hash: str, user_id: int) -> Optional[int]:
    result = database.temp_session.query(DBRating.rating) \
            .filter(DBRating.map_checksum == beatmap_hash) \
            .filter(DBRating.user_id == user_id) \
            .first()

    return result[0] if result else None

def fetch_many(beatmap_hash) -> List[int]:
    return [
        rating[0]
        for rating in database.temp_session.query(DBRating.rating) \
            .filter(DBRating.map_checksum == beatmap_hash) \
            .all()
    ]

def fetch_average(beatmap_hash) -> float:
    result = database.temp_session.query(
        func.avg(DBRating.rating) \
            .label('average')) \
        .filter(DBRating.map_checksum == beatmap_hash) \
        .first()[0]

    return float(result) if result else None
