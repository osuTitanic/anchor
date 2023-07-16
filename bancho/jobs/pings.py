
from datetime import datetime

import bancho
import time

PING_INTERVAL = 30
TIMEOUT_SECS  = 45

def ping():
    while True:
        next_ping = datetime.now().timestamp() - PING_INTERVAL

        for player in bancho.services.players:
            if player.is_bot:
                continue
            
            # Enqueue ping if needed
            if (next_ping > player.last_response.timestamp()):
                player.handler.enqueue_ping()

            last_response = datetime.now().timestamp() - player.last_response.timestamp()

            # Check timeout
            if last_response >= TIMEOUT_SECS:
                player.logger.warning('Client timed out')
                player.closeConnection()

        if bancho.services.jobs._shutdown:
            exit()

        time.sleep(1)

bancho.services.jobs.submit(ping)
