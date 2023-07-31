
from app.common.database.objects import DBComment
from typing import List

import app

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
    with app.session.database.session as session:
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
    return app.session.database.temp_session.query(DBComment) \
            .filter(DBComment.target_id == target_id) \
            .filter(DBComment.target_type == type) \
            .order_by(DBComment.time.asc()) \
            .all()
