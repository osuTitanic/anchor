
from app.common.database import DBRelationship
from app.session import database

from typing import List

def create(
    user_id: int,
    target_id: int,
    status: int = 0
) -> DBRelationship:
    with database.session as session:
        session.add(
            rel := DBRelationship(
                user_id,
                target_id,
                status
            )
        )
        session.commit()

    return rel

def delete(
    user_id: int,
    target_id: int,
    status: int = 0
) -> bool:
    with database.session as session:
        rel = session.query(DBRelationship) \
                .filter(DBRelationship.user_id == user_id) \
                .filter(DBRelationship.target_id == target_id) \
                .filter(DBRelationship.status == status)

        if rel.first():
            rel.delete()
            session.commit()
            return True

        return False

def fetch_many_by_id(user_id: int) -> List[DBRelationship]:
    return database.temp_session.query(DBRelationship) \
               .filter(DBRelationship.user_id == user_id) \
               .all()

def fetch_many_by_target(target_id: int) -> List[DBRelationship]:
    return database.temp_session.query(DBRelationship) \
               .filter(DBRelationship.target_id == target_id) \
               .all()

def fetch_count_by_id(user_id: int) -> int:
    return database.temp_session.query(DBRelationship) \
               .filter(DBRelationship.user_id == user_id) \
               .count()

def fetch_count_by_target(target_id: int) -> int:
    return database.temp_session.query(DBRelationship) \
               .filter(DBRelationship.target_id == target_id) \
               .count()
