
from app.common.database import DBScreenshot
from app.session import database

from typing import Optional

def create(user_id: int, hidden: bool) -> DBScreenshot:
    with database.session as session:
        session.add(
            ss := DBScreenshot(
                user_id,
                hidden
            )
        )
        session.commit()

    return ss

def fetch_by_id(id: int) -> Optional[DBScreenshot]:
    return database.temp_session.query(DBScreenshot) \
        .filter(DBScreenshot.id == id) \
        .first()
