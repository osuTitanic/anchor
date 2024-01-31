
from app.common.cache import leaderboards
from app.common.database import users

import app

def index_ranks():
    """
    This will run on startup as a background job, and check if the redis leaderboards are empty.
    It will then try to re-index every active player in the leaderboards.
    This should actually never happen, but it can be useful in emergency situations.
    """
    if not leaderboards.top_players(0):
        with app.session.database.managed_session() as session:
            # Redis cache was flushed
            active_players = users.fetch_all(session=session)

            app.session.logger.info(f'Indexing player ranks... ({len(active_players)})')

            for player in active_players:
                for stats in player.stats:
                    leaderboards.update(
                        stats,
                        player.country.lower()
                    )

            app.session.logger.info('Index complete!')
