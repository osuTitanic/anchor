
from threading import Thread

import bancho
import time
import json

def user_update(user_id: int):
    if not (player := bancho.services.players.by_id(user_id)):
        return

    player.update()

def bot_message(message: str, target: str):
    if not (channel := bancho.services.channels.by_name(target)):
        return

    messages = message.split('\n')

    for message in messages:
        channel.send_message(bancho.services.bot_player, message)

def restrict(user_id: int, reason: str = ''):
    if not (player := bancho.services.players.by_id(user_id)):
        return

    player.restrict(reason, autoban=True)

def announcement(message: str):
    bancho.services.players.announce(message)

def queue_updates():
    while True:
        tasks = bancho.services.cache.redis.lrange(
            'bancho:queue',
            0, -1
        )

        for data in tasks:
            try:
                task = json.loads(data.decode())
                func = eval(task['type'])

                Thread(
                    target=func,
                    kwargs=(task['data']),
                    daemon=True
                ).start()
            except NameError:
                bancho.services.logger.warning(
                    f'Queue task with name {task["type"]} was not found.'
                )
            except json.JSONDecodeError:
                bancho.services.logger.warning(
                    f'Failed to parse task with data: "{data}"'
                )
            except Exception as e:
                bancho.services.logger.error(
                    f'Failed to run task: "{e}"'
                )
            finally:
                bancho.services.cache.redis.lpop('bancho:queue', 1)

        if bancho.services.jobs._shutdown:
            exit()

        time.sleep(1)

bancho.services.jobs.submit(queue_updates)

