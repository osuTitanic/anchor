
from app.common.database import DBAchievement
from app.common.objects import Achievement
from app.session import database

from typing import List

def create_many(
    achievements: List[Achievement],
    user_id: int
) -> None:
    with database.session as session:
        for a in achievements:
            session.add(
                DBAchievement(
                    user_id,
                    a.name,
                    a.category,
                    a.filename
                )
            )

        session.commit()

def fetch_many(user_id: int) -> List[DBAchievement]:
    return database.temp_session.query(DBAchievement) \
            .filter(DBAchievement.user_id == user_id) \
            .all()
