
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.exc import ResourceClosedError
from sqlalchemy     import create_engine

from typing import Generator
from threading import Timer

from .objects import Base

import traceback
import logging

class Postgres:
    def __init__(self, username: str, password: str, host: str, port: int) -> None:
        self.engine = create_engine(
            f'postgresql://{username}:{password}@{host}:{port}/{username}',
            max_overflow=30,
            pool_size=15,
            echo=False
        )

        self.logger = logging.getLogger('postgres')
        Base.metadata.create_all(bind=self.engine)

        self.session_factory = scoped_session(
            sessionmaker(self.engine, expire_on_commit=False, autoflush=True)
        )

    @property
    def session(self) -> Session:
        return self.session_factory()

    @property
    def temp_session(self) -> Session:
        for session in self.create_temp_session():
            return session

    def create_temp_session(self, timeout: int = 15) -> Generator:
        session = self.session_factory()
        try:
            yield session
        except Exception as e:
            traceback.print_exc()
            self.logger.critical(f'Transaction failed: "{e}". Performing rollback...')
            session.rollback()
        finally:
            Timer(
                interval=timeout,
                function=self.close_session,
                args=[session]
            ).start()

    def close_session(self, session: Session) -> None:
        try:
            session.close()
        except AttributeError:
            pass
        except ResourceClosedError:
            pass
        except Exception as exc:
            traceback.print_exc()
            self.logger.error(
                f'Failed to close session: {exc}'
            )
