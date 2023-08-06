
from app.common.database.objects import DBRelationship
from typing import List

import app

def create(
    user_id: int,
    target_id: int,
    status: int = 0
) -> DBRelationship:
    with app.session.database.session as session:
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
    with app.session.database.session as session:
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
    return app.session.database.pool_session.query(DBRelationship) \
               .filter(DBRelationship.user_id == user_id) \
               .all()

def fetch_many_by_target(target_id: int) -> List[DBRelationship]:
    return app.session.database.pool_session.query(DBRelationship) \
               .filter(DBRelationship.target_id == target_id) \
               .all()

def fetch_count_by_id(user_id: int) -> int:
    return app.session.database.pool_session.query(DBRelationship) \
               .filter(DBRelationship.user_id == user_id) \
               .count()

def fetch_count_by_target(target_id: int) -> int:
    return app.session.database.pool_session.query(DBRelationship) \
               .filter(DBRelationship.target_id == target_id) \
               .count()
