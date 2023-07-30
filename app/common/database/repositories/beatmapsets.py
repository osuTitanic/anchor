
from app.common.database import DBBeatmapset
from app.session import database

from typing import Optional

# TODO: create

def fetch_one(id: int) -> Optional[DBBeatmapset]:
    return database.temp_session.query(DBBeatmapset) \
                .filter(DBBeatmapset.id == id) \
                .first()
