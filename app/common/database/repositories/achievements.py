
from app.common.database.objects import DBAchievement
from app.common.objects import bAchievement

from typing import List

import app

def create_many(
    achievements: List[bAchievement],
    user_id: int
) -> None:
    with app.session.database.session as session:
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
    return app.session.database.temp_session.query(DBAchievement) \
            .filter(DBAchievement.user_id == user_id) \
            .all()
