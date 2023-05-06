
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy     import create_engine

from typing import Optional, Generator, List

from .objects import (
    DBChannel,
    DBUser,
    Base
)

import traceback
import bancho

class Postgres:
    def __init__(self, username: str, password: str, host: str, port: int) -> None:
        self.engine = create_engine(
            f'postgresql://{username}:{password}@{host}:{port}/{username}', 
            echo=False
        )

        Base.metadata.create_all(bind=self.engine)

        self.session_factory = scoped_session(
            sessionmaker(self.engine, expire_on_commit=False, autoflush=True)
        )
    
    @property
    def session(self) -> Session:
        for session in self.create_session():
            return session

    def create_session(self) -> Generator:
        session = self.session_factory()
        try:
            yield session
        except Exception as e:
            traceback.print_exc()
            bancho.services.logger.critical(f'Transaction failed: "{e}". Performing rollback...')
            session.rollback()
        finally:
            session.close()

    def user_by_name(self, name: str) -> Optional[DBUser]:
        return self.session.query(DBUser).filter(DBUser.name == name).first()
    
    def user_by_id(self, id: int) -> Optional[DBUser]:
        return self.session.query(DBUser).filter(DBUser.id == id).first()
    
    def channels(self) -> List[DBChannel]:
        return self.session.query(DBChannel).all()
