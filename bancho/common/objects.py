
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from datetime import datetime

from sqlalchemy import (
    SmallInteger,
    LargeBinary,
    ForeignKey,
    BigInteger,
    DateTime,
    Boolean,
    Integer,
    Column,
    String,
    Float,
)

Base = declarative_base()

class DBAchievement(Base):
    __tablename__ = "achievements"

    user_id     = Column('user_id', Integer, ForeignKey('users.id'), primary_key=True)
    name        = Column('name', String, primary_key=True)
    category    = Column('category', String)
    filename    = Column('filename', String)
    unlocked_at = Column('unlocked_at', DateTime)

    user = relationship('DBUser', back_populates='achievements')

class DBStats(Base):
    __tablename__ = "stats"

    user_id      = Column('id', Integer, ForeignKey('users.id'), primary_key=True)
    mode         = Column('mode', SmallInteger, primary_key=True)

    rank         = Column('rank', Integer, default=0)
    tscore       = Column('tscore', BigInteger, default=0)
    rscore       = Column('rscore', BigInteger, default=0)
    pp           = Column('pp', Float, default=0.0)
    playcount    = Column('playcount', BigInteger, default=0)
    playtime     = Column('playtime', Integer, default=0)
    acc          = Column('acc', Float, default=0.0)
    max_combo    = Column('max_combo', Integer, default=0)
    total_hits   = Column('total_hits', Integer, default=0)
    replay_views = Column('replay_views', Integer, default=0)

    xh_count  = Column('xh_count', Integer, default=0)
    x_count   = Column('x_count', Integer, default=0)
    sh_count  = Column('sh_count', Integer, default=0)
    s_count   = Column('s_count', Integer, default=0)
    a_count   = Column('a_count', Integer, default=0)
    b_count   = Column('b_count', Integer, default=0)
    c_count   = Column('c_count', Integer, default=0)
    d_count   = Column('d_count', Integer, default=0)

    user = relationship('DBUser', back_populates='stats')

    def __init__(self, user_id: int, mode: int) -> None:
        self.user_id = user_id
        self.mode    = mode

class DBScore(Base):
    __tablename__ = "scores"

    id             = Column('id', BigInteger, primary_key=True, autoincrement=True)
    user_id        = Column('user_id', Integer, ForeignKey('users.id'))
    beatmap_id     = Column('beatmap_id', Integer, ForeignKey('beatmaps.id'))
    client_version = Column('client_version', String)
    client_hash    = Column('client_hash', String)
    checksum       = Column('score_checksum', String)
    mode           = Column('mode', SmallInteger)
    pp             = Column('pp', Float)
    acc            = Column('acc', Float)
    total_score    = Column('total_score', BigInteger)
    max_combo      = Column('max_combo', Integer)
    mods           = Column('mods', Integer)
    perfect        = Column('perfect', Boolean)
    n300           = Column('n300', Integer)
    n100           = Column('n100', Integer)
    n50            = Column('n50', Integer)
    nMiss          = Column('nmiss', Integer)
    nGeki          = Column('ngeki', Integer)
    nKatu          = Column('nkatu', Integer)
    grade          = Column('grade', String, default='N')
    status         = Column('status', SmallInteger, default=-1)
    submitted_at   = Column('submitted_at', DateTime, default=datetime.now())

    replay_md5     = Column('replay_md5', String, nullable=True)
    processes      = Column('processes',  String, nullable=True)
    failtime       = Column('failtime',  Integer, nullable=True)

    user    = relationship('DBUser', back_populates='scores')
    beatmap = relationship('DBBeatmap', back_populates='scores')

class DBPlay(Base):
    __tablename__ = "plays"

    user_id      = Column('user_id', Integer, ForeignKey('users.id'), primary_key=True)
    beatmap_id   = Column('beatmap_id', Integer, ForeignKey('beatmaps.id'), primary_key=True)
    set_id       = Column('set_id', Integer, ForeignKey('beatmapsets.id'))
    count        = Column('count', Integer)
    beatmap_file = Column('beatmap_file', String)

    user       = relationship('DBUser', back_populates='plays')
    beatmap    = relationship('DBBeatmap', back_populates='plays')
    beatmapset = relationship('DBBeatmapset', back_populates='plays')

class DBFavourite(Base):
    __tablename__ = "favourites"

    user_id    = Column('user_id', Integer, ForeignKey('users.id'), primary_key=True)
    set_id     = Column('set_id', Integer, ForeignKey('beatmapsets.id'), primary_key=True)
    created_at = Column('created_at', DateTime, default=datetime.now())

    user       = relationship('DBUser', back_populates='favourites')
    beatmapset = relationship('DBBeatmapset', back_populates='favourites')

class DBRating(Base):
    __tablename__ = "ratings"

    user_id      = Column('user_id', Integer, ForeignKey('users.id'), primary_key=True)
    set_id       = Column('set_id', Integer, ForeignKey('beatmapsets.id'))
    map_checksum = Column('map_checksum', String, ForeignKey('beatmaps.md5'), primary_key=True)
    rating       = Column('rating', SmallInteger)

    user       = relationship('DBUser', back_populates='ratings')
    beatmap    = relationship('DBBeatmap', back_populates='ratings')
    beatmapset = relationship('DBBeatmapset', back_populates='ratings')

class DBScreenshot(Base):
    __tablename__ = "screenshots"

    id         = Column('id', Integer, primary_key=True, autoincrement=True)
    user_id    = Column('user_id', ForeignKey('users.id'))
    created_at = Column('created_at', DateTime, default=datetime.now())
    hidden     = Column('hidden', Boolean, default=False)

    user = relationship('DBUser', back_populates='screenshots')

class DBRelationship(Base):
    __tablename__ = "relationships"

    user_id   = Column('user_id', Integer, ForeignKey('users.id'), primary_key=True)
    target_id = Column('target_id', Integer, primary_key=True)
    status    = Column('status', SmallInteger)

    user = relationship('DBUser', back_populates='relationships')

    def __init__(self, user: int, target: int, status: int) -> None:
        self.user_id = user
        self.target_id = target
        self.status = status

class DBComment(Base):
    __tablename__ = "comments"

    id          = Column('id', Integer, primary_key=True, autoincrement=True)
    target_id   = Column('target_id', Integer)
    target_type = Column('target_type', String)
    user_id     = Column('user_id', Integer, ForeignKey('users.id'))
    time        = Column('time', DateTime, default=datetime.now())
    comment     = Column('comment', String)
    format      = Column('format', String, nullable=True)
    mode        = Column('mode', SmallInteger, default=0)

class DBLog(Base):
    __tablename__ = "logs"

    id      = Column('id', Integer, primary_key=True, autoincrement=True)
    level   = Column('level', String)
    type    = Column('type', String)
    message = Column('message', String)
    time    = Column('time', DateTime, default=datetime.now())

    def __init__(self, message: str, level: str, type: str) -> None:
        self.message = message
        self.level   = level
        self.type    = type

class DBChannel(Base):
    __tablename__ = "channels"

    name              = Column('name', String, primary_key=True)
    topic             = Column('topic', String)
    read_permissions  = Column('read_permissions', Integer, default=1)
    write_permissions = Column('write_permissions', Integer, default=1)

class DBMessage(Base):
    __tablename__ = "messages"

    id      = Column('id', Integer, primary_key=True, autoincrement=True)
    sender  = Column('sender', String, ForeignKey('users.name'))
    target  = Column('target', String) # Either channel or username
    message = Column('message', String)
    time    = Column('time', DateTime, default=datetime.now())

    def __init__(self, sender: str, target: str, message: str) -> None:
        self.message = message
        self.sender  = sender
        self.target  = target

class DBBeatmapset(Base):
    __tablename__ = "beatmapsets"

    id          = Column('id', Integer, primary_key=True, autoincrement=True)
    title       = Column('title', String, nullable=True)
    artist      = Column('artist', String, nullable=True)
    creator     = Column('creator', String, nullable=True)
    source      = Column('source', String, nullable=True)
    tags        = Column('tags', String, nullable=True, default='')
    status      = Column('submission_status', Integer, default=3)
    has_video   = Column('has_video', Boolean, default=False)
    server      = Column('server', SmallInteger, default=0)
    available   = Column('available', Boolean, default=True)
    created_at  = Column('submission_date', DateTime, default=datetime.now())
    approved_at = Column('approved_date', DateTime, nullable=True)
    last_update = Column('last_updated', DateTime, default=datetime.now())
    added_at    = Column('added_at', DateTime, nullable=True) # only if server is 0 (osu!)

    favourites = relationship('DBFavourite', back_populates='beatmapset')
    beatmaps   = relationship('DBBeatmap', back_populates='beatmapset')
    ratings    = relationship('DBRating', back_populates='beatmapset')
    plays      = relationship('DBPlay', back_populates='beatmapset')

class DBBeatmap(Base):
    __tablename__ = "beatmaps"

    id           = Column('id', Integer, primary_key=True, autoincrement=True)
    set_id       = Column('set_id', Integer, ForeignKey('beatmapsets.id'))
    mode         = Column('mode', SmallInteger, default=0)
    md5          = Column('md5', String)
    status       = Column('status', SmallInteger, default=2)
    version      = Column('version', String)
    filename     = Column('filename', String)
    created_at   = Column('submission_date', DateTime, default=datetime.now())
    last_update  = Column('last_updated', DateTime, default=datetime.now())
    playcount    = Column('playcount', BigInteger, default=0)
    passcount    = Column('passcount', BigInteger, default=0)
    total_length = Column('total_length', Integer)

    max_combo = Column('max_combo', Integer)
    bpm       = Column('bpm',  Float, default=0.0)
    cs        = Column('cs',   Float, default=0.0)
    ar        = Column('ar',   Float, default=0.0)
    od        = Column('od',   Float, default=0.0)
    hp        = Column('hp',   Float, default=0.0)
    diff      = Column('diff', Float, default=0.0)

    beatmapset = relationship('DBBeatmapset', back_populates='beatmaps')
    ratings    = relationship('DBRating', back_populates='beatmap')
    scores     = relationship('DBScore', back_populates='beatmap')
    plays      = relationship('DBPlay', back_populates='beatmap')

    def __repr__(self) -> str:
        return f'<Beatmap ({self.id}) {self.beatmapset.artist} - {self.beatmapset.title} [{self.version}]>'

    @property
    def full_name(self):
        return f'{self.beatmapset.artist} - {self.beatmapset.title} [{self.version}]'

class DBBadge(Base):
    __tablename__ = "profile_badges"

    id                = Column('id', Integer, primary_key=True, autoincrement=True)
    user_id           = Column('user_id', Integer, ForeignKey('users.id'))
    created           = Column('created', DateTime, default=datetime.now())
    badge_icon        = Column('badge_icon', String)
    badge_url         = Column('badge_url', String, nullable=True)
    badge_description = Column('badge_description', String, nullable=True)

    user = relationship('DBUser', back_populates='badges')

class DBActivity(Base):
    __tablename__ = "profile_activity"

    id             = Column('id', Integer, primary_key=True, autoincrement=True)
    user_id        = Column('user_id', Integer, ForeignKey('users.id'))
    time           = Column('time', DateTime, default=datetime.now())
    activity_text  = Column('activity_text', String)
    activity_args  = Column('activity_args', String, nullable=True)
    activity_links = Column('activity_links', String, nullable=True)

    user = relationship('DBUser', back_populates='activity')

class DBName(Base):
    __tablename__ = "name_history"

    id         = Column('id', Integer, primary_key=True, autoincrement=True)
    user_id    = Column('user_id', Integer, ForeignKey('users.id'))
    changed_at = Column('changed_at', DateTime, default=datetime.now())
    name       = Column('name', String)

    user = relationship('DBUser', back_populates='names')

class DBRankHistory(Base):
    __tablename__ = "profile_rank_history"

    user_id      = Column('user_id', Integer, ForeignKey('users.id'), primary_key=True)
    time         = Column('time', DateTime, default=datetime.now(), primary_key=True)
    rscore       = Column('rscore', BigInteger)
    pp           = Column('pp', Integer)
    global_rank  = Column('global_rank', Integer)
    country_rank = Column('country_rank', Integer)
    score_rank   = Column('score_rank', Integer)

    user = relationship('DBUser', back_populates='rank_history')

class DBPlayHistory(Base):
    __tablename__ = "profile_play_history"

    user_id = Column('user_id', Integer, ForeignKey('users.id'), primary_key=True)
    year    = Column('year', Integer, primary_key=True)
    month   = Column('month', Integer, primary_key=True)
    plays   = Column('plays', Integer, default=0)

    user = relationship('DBUser', back_populates='play_history')

class DBReplayHistory(Base):
    __tablename__ = "profile_replay_history"

    user_id      = Column('user_id', Integer, ForeignKey('users.id'), primary_key=True)
    year         = Column('year', Integer, primary_key=True)
    month        = Column('month', Integer, primary_key=True)
    replay_views = Column('replay_views', Integer, default=0)

    user = relationship('DBUser', back_populates='replay_history')

class DBUser(Base):
    __tablename__ = "users"

    id               = Column('id',               Integer, primary_key=True, autoincrement=True)
    name             = Column('name',             String, unique=True)
    safe_name        = Column('safe_name',        String, unique=True)
    email            = Column('email',            String, unique=True)
    bcrypt           = Column('pw',               String)
    permissions      = Column('permissions',      Integer, default=1)
    country          = Column('country',          String)
    silence_end      = Column('silence_end',      DateTime, nullable=True)
    supporter_end    = Column('supporter_end',    DateTime, nullable=True)
    created_at       = Column('created_at',       DateTime, default=datetime.now())
    latest_activity  = Column('latest_activity',  DateTime, default=datetime.now())
    restricted       = Column('restricted',       Boolean, default=False)
    activated        = Column('activated',        Boolean, default=False)
    preferred_mode   = Column('preferred_mode',   Integer, default=0)
    playstyle        = Column('playstyle',        Integer, default=0)
    userpage_content = Column('userpage_content', String, nullable=True)
    userpage_title   = Column('userpage_title',   String, nullable=True)

    replay_history = relationship('DBReplayHistory', back_populates='user')
    relationships  = relationship('DBRelationship', back_populates='user')
    rank_history   = relationship('DBRankHistory', back_populates='user')
    play_history   = relationship('DBPlayHistory', back_populates='user')
    achievements   = relationship('DBAchievement', back_populates='user')
    screenshots    = relationship('DBScreenshot', back_populates='user')
    favourites     = relationship('DBFavourite', back_populates='user')
    activity       = relationship('DBActivity', back_populates='user')
    ratings        = relationship('DBRating', back_populates='user')
    scores         = relationship('DBScore', back_populates='user')
    stats          = relationship('DBStats', back_populates='user')
    badges         = relationship('DBBadge', back_populates='user')
    names          = relationship('DBName', back_populates='user')
    plays          = relationship('DBPlay', back_populates='user')
