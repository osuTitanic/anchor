
from app.common.database import DBComment
from app.session import database

from typing import List

def create(
    target_id: int,
    target: str,
    user_id: int,
    time: int,
    content: str,
    comment_format: str,
    playmode: int,
    color: str
) -> DBComment:
    with database.session as session:
        session.add(
            c := DBComment(
                target_id,
                target,
                user_id,
                time,
                content,
                comment_format,
                playmode,
                color
            )
        )
        session.commit()

    return c

def fetch_many(
    target_id: int,
    type: str
) -> List[DBComment]:
    return database.temp_session.query(DBComment) \
            .filter(DBComment.target_id == target_id) \
            .filter(DBComment.target_type == type) \
            .order_by(DBComment.time.asc()) \
            .all()
