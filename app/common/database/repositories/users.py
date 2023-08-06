
from app.common.database.objects import DBUser
from typing import Optional

import app

def create(
    username: str,
    email: str,
    pw_bcrypt: str,
    country: str
) -> DBUser:
    with app.session.database.session as session:
        session.add(
            user := DBUser(
                username,
                email,
                pw_bcrypt,
                country
            )
        )
        session.commit()

    return user

def update(user_id: int, updates: dict) -> int:
    with app.session.database.session as session:
        rows = session.query(DBUser) \
               .filter(DBUser.id == user_id) \
               .update(updates)
        session.commit()

    return rows

def fetch_by_name(username: str) -> Optional[DBUser]:
    return app.session.database.pool_session.query(DBUser) \
        .filter(DBUser.name == username) \
        .first()

def fetch_by_id(id: int) -> Optional[DBUser]:
    return app.session.database.pool_session.query(DBUser) \
        .filter(DBUser.id == id) \
        .first()
