
from typing import Optional, Tuple, List

import app

def update(
    user_id: int,
    mode: int,
    pp: float,
    score: int,
    country: str
) -> None:
    """Update global, country and score ranks"""
    if pp <= 0:
        return

    # Global
    app.session.redis.zadd(
        f'bancho:performance:{mode}',
        {user_id: pp}
    )

    # Country
    app.session.redis.zadd(
        f'bancho:performance:{mode}:{country}',
        {user_id: pp}
    )

    if score <= 0:
        return

    # Score
    app.session.redis.zadd(
        f'bancho:rscore:{mode}',
        {user_id: score}
    )

def remove(
    user_id: int,
    country: str
) -> None:
    """Remove player from leaderboards"""
    for mode in range(4):
        app.session.redis.zrem(
            f'bancho:performance:{mode}',
            user_id
        )

        app.session.redis.zrem(
            f'bancho:performance:{mode}:{country}',
            user_id
        )

        app.session.redis.zrem(
            f'bancho:rscore:{mode}',
            user_id
        )

def global_rank(
    user_id: int,
    mode: int
) -> int:
    """Get global rank"""
    rank = app.session.redis.zrevrank(
        f'bancho:performance:{mode}',
        user_id
    )
    return (rank + 1 if rank is not None else 0)

def country_rank(
    user_id: int,
    mode: int,
    country: str
) -> int:
    """Get country rank"""
    rank = app.session.redis.zrevrank(
        f'bancho:performance:{mode}:{country}',
        user_id
    )
    return (rank + 1 if rank is not None else 0)

def score_rank(
    user_id: int,
    mode: int
) -> int:
    """Get score rank"""
    rank = app.session.redis.zrevrank(
        f'bancho:rscore:{mode}',
        user_id
    )
    return (rank + 1 if rank is not None else 0)

def performance(
    user_id: int,
    mode: int
) -> int:
    """Get player's pp""" # this sounds wrong
    pp = app.session.redis.zscore(
        f'bancho:performace:{mode}',
        user_id
    )
    return pp if pp is not None else 0

def score(
    user_id: int,
    mode: int
) -> int:
    """Get player's ranked score"""
    score = app.session.redis.zscore(
        f'bancho:rscore:{mode}',
        user_id
    )
    return score if score is not None else 0

def top_players(
    mode: int,
    offset: int = 0,
    range: int = 50,
    type: str = 'performance',
    country: Optional[str] = None
) -> List[Tuple[int, float]]:
    """Get a list of top players

    `returns`: List[Tuple[player_id, score/pp]]
    """
    players = app.session.redis.zrevrange(
        f'bancho:{type}:{mode}{f":{country}" if country else ""}',
        offset,
        range,
        withscores=True
    )

    return [(int(id), score) for id, score in players]
