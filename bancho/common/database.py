
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.exc import ResourceClosedError
from sqlalchemy     import create_engine

from typing import Optional, Generator, List
from threading import Timer, Thread
from datetime import datetime

from .objects import (
    DBRelationship,
    DBRankHistory,
    DBBeatmap,
    DBMessage,
    DBChannel,
    DBScore,
    DBStats,
    DBUser,
    DBLog,
    Base
)

import traceback
import logging
import bancho

class Postgres:
    def __init__(self, username: str, password: str, host: str, port: int) -> None:
        self.logger = logging.getLogger('postgres')
        self.engine = create_engine(
            f'postgresql://{username}:{password}@{host}:{port}/{username}',
            max_overflow=30,
            pool_size=15,
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
            self.logger.critical(f'Transaction failed: "{e}". Performing rollback...')
            session.rollback()
        finally:
            Timer(
                interval=15,
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
            self.logger.error(f'Failed to close session: {exc}')

    def user_by_name(self, name: str) -> Optional[DBUser]:
        return self.session.query(DBUser) \
                .filter(DBUser.name == name) \
                .first()
    
    def user_by_id(self, id: int) -> Optional[DBUser]:
        return self.session.query(DBUser) \
                .filter(DBUser.id == id) \
                .first()
    
    def beatmap_by_file(self, filename: str) -> Optional[DBBeatmap]:
        return self.session.query(DBBeatmap) \
                .filter(DBBeatmap.filename == filename) \
                .first()
    
    def beatmap_by_checksum(self, md5: str) -> Optional[DBBeatmap]:
        return self.session.query(DBBeatmap) \
                .filter(DBBeatmap.md5 == md5) \
                .first()
    
    def personal_best(self, beatmap_id: int, user_id: int, mode: int) -> Optional[DBScore]:
        return self.session.query(DBScore) \
                .filter(DBScore.beatmap_id == beatmap_id) \
                .filter(DBScore.user_id == user_id) \
                .filter(DBScore.mode == mode) \
                .filter(DBScore.status == 3) \
                .first()
    
    def channels(self) -> List[DBChannel]:
        return self.session.query(DBChannel).all()
    
    def stats(self, user_id: int, mode: int) -> Optional[DBStats]:
        return self.session.query(DBStats) \
                .filter(DBStats.user_id == user_id) \
                .filter(DBStats.mode == mode) \
                .first()
    
    def relationships(self, user_id: int) -> List[DBStats]:
        return self.session.query(DBRelationship) \
                .filter(DBRelationship.user_id == user_id) \
                .all()
    
    def add_relationship(self, user_id: int, target_id: int, friend: bool = True) -> DBRelationship:
        instance = self.session
        instance.add(
            rel := DBRelationship(
                user_id,
                target_id,
                int(not friend)
            )
        )
        instance.commit()

        return rel
    
    def remove_relationship(self, user_id: int, target_id: int, status: int = 0):
        instance = self.session
        rel = instance.query(DBRelationship) \
                .filter(DBRelationship.user_id == user_id) \
                .filter(DBRelationship.target_id == target_id) \
                .filter(DBRelationship.status == status)

        if rel.first():
            rel.delete()
            instance.commit()
    
    def submit_log(self, message: str, level: str, log_type: str):
        instance = self.session
        instance.add(
            DBLog(
                message,
                level,
                log_type
            )
        )
        instance.commit()
    
    def submit_message(self, sender: str, target: str, message: str):
        instance = self.session
        instance.add(
            DBMessage(
                sender,
                target,
                message
            )
        )
        instance.commit()

    def update_latest_activity(self, user_id: int):
        Thread(
            target=self.__update_latest_activity,
            args=[user_id],
            daemon=True
        ).start()

    def __update_latest_activity(self, user_id: int):
        instance = self.session
        instance.query(DBUser) \
                .filter(DBUser.id == user_id) \
                .update({
                    'latest_activity': datetime.now()
                })
        instance.commit()

    def update_rank_history(self, stats: DBStats):
        country_rank = bancho.services.cache.get_country_rank(stats.user_id, stats.mode, stats.user.country)
        global_rank = bancho.services.cache.get_global_rank(stats.user_id, stats.mode)
        score_rank = bancho.services.cache.get_score_rank(stats.user_id, stats.mode)

        if global_rank <= 0:
            return

        instance = self.session
        instance.add(
            DBRankHistory(
                stats.user_id,
                stats.mode,
                stats.rscore,
                stats.pp,
                global_rank,
                country_rank,
                score_rank
            )
        )
        instance.commit()
