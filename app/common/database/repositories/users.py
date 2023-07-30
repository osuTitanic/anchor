
from app.common.database import DBUser
from app.session import database

from typing import Optional

def create(
    username: str,
    email: str,
    pw_bcrypt: str,
    country: str
) -> DBUser:
    with database.session as session:
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
    with database.session as session:
        rows = session.query(DBUser) \
               .filter(DBUser.id == user_id) \
               .update(updates)
        session.commit()

    return rows

def fetch_by_name(username: str) -> Optional[DBUser]:
    return database.temp_session.query(DBUser) \
        .filter(DBUser.name == username) \
        .first()

def fetch_by_id(id: int) -> Optional[DBUser]:
    return database.temp_session.query(DBUser) \
        .filter(DBUser.id == id) \
        .first()
