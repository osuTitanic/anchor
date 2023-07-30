
from app.common.database import DBFavourite
from app.session import database

from typing import List, Optional

def create(
    user_id: int,
    set_id: int
) -> DBFavourite:
    with database.session as session:
        # Check if favourite was already set
        if session.query(DBFavourite.user_id) \
            .filter(DBFavourite.user_id == user_id) \
            .filter(DBFavourite.set_id == set_id) \
            .first():
            return

        session.add(
            fav := DBFavourite(
                user_id,
                set_id
            )
        )
        session.commit()

    return fav

def fetch_one(
    user_id: int,
    set_id: int
) -> Optional[DBFavourite]:
    return database.temp_session.query(DBFavourite) \
            .filter(DBFavourite.user_id == user_id) \
            .filter(DBFavourite.set_id == set_id) \
            .first()

def fetch_many(user_id: int) -> List[DBFavourite]:
    return database.temp_session.query(DBFavourite) \
            .filter(DBFavourite.user_id == user_id) \
            .all()
