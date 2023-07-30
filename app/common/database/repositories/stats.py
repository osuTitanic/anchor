
from app.common.database import DBStats
from app.session import database

from typing import Optional, List

def create(user_id: int, mode: int) -> DBStats:
    with database.session as session:
        session.add(
            stats := DBStats(
                user_id,
                mode
            )
        )
        session.commit()

    return stats

def update(user_id: int, mode: int, updates: dict) -> int:
    with database.session as session:
        rows = session.query(DBStats) \
               .filter(DBStats.user_id == user_id) \
               .filter(DBStats.mode == mode) \
               .update(updates)
        session.commit()

    return rows

def fetch_by_mode(user_id: int,  mode: int) -> Optional[DBStats]:
    return database.temp_session.query(DBStats) \
        .filter(DBStats.user_id == user_id) \
        .filter(DBStats.mode == mode) \
        .first()

def fetch_all(user_id: int) -> List[DBStats]:
    return database.temp_session.query(DBStats) \
        .filter(DBStats.user_id == user_id) \
        .first()
