
from datetime import datetime

import bancho
import time

PING_INTERVAL = 30

def ping():
    while True:
        next_ping = datetime.now().timestamp() - PING_INTERVAL

        for player in bancho.services.players:
            if (
                next_ping > player.last_response.timestamp()
               ):
                player.handler.enqueue_ping()

        if bancho.services.jobs._shutdown:
            exit()

        time.sleep(1)

bancho.services.jobs.submit(ping)
