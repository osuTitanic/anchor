
from app.common.database.objects import DBBeatmapset
from typing import Optional

import app

# TODO: create

def fetch_one(id: int) -> Optional[DBBeatmapset]:
    return app.session.database.pool_session.query(DBBeatmapset) \
                .filter(DBBeatmapset.id == id) \
                .first()
