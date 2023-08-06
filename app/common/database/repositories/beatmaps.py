
from app.common.database.objects import DBBeatmap
from typing import Optional, List

import app

# TODO: create

def fetch_by_id(id: int) -> Optional[DBBeatmap]:
    return app.session.database.pool_session.query(DBBeatmap) \
                .filter(DBBeatmap.id == id) \
                .first()

def fetch_by_file(filename: str) -> Optional[DBBeatmap]:
    return app.session.database.pool_session.query(DBBeatmap) \
                .filter(DBBeatmap.filename == filename) \
                .first()

def fetch_by_checksum(checksum: str) -> Optional[DBBeatmap]:
    return app.session.database.pool_session.query(DBBeatmap) \
                .filter(DBBeatmap.md5 == checksum) \
                .first()

def fetch_by_set(set_id: int) -> List[DBBeatmap]:
    return app.session.database.pool_session.query(DBBeatmap) \
                .filter(DBBeatmap.set_id == set_id) \
                .all()
