
from app.common.constants import ANCHOR_ASCII_ART
from app.common.helpers import location

from twisted.python.failure import Failure

import config
import struct
import socket
import app
import os

def setup():
    app.session.logger.info(f'{ANCHOR_ASCII_ART}\n    anchor-{config.VERSION}\n')
    os.makedirs(config.DATA_PATH, exist_ok=True)

def is_local_ip(ip: str) -> bool:
    private = (
        [ 2130706432, 4278190080 ], # 127.0.0.0
        [ 3232235520, 4294901760 ], # 192.168.0.0
        [ 2886729728, 4293918720 ], # 172.16.0.0
        [ 167772160,  4278190080 ], # 10.0.0.0
    )

    f = struct.unpack(
        '!I',
        socket.inet_pton(
            socket.AF_INET,
            ip
        )
    )[0]

    for net in private:
        if (f & net[1]) == net[0]:
            return True

    return False

def thread_callback(error: Failure):
    app.session.logger.error(
        f'Failed to execute thread: {error.__str__()} ({error.getErrorMessage()})',
        exc_info=error.value
    )

def valid_client_hash(hash: str) -> bool:
    try:
        if not (manifest := app.session.client_manifest):
            response = app.session.requests.get(f'http://osu.{config.DOMAIN_NAME}/clients/manifest.json')

            if not response.ok:
                return True

            app.session.client_manifest = response.json()
            return valid_client_hash(hash)

    except ConnectionError:
        app.session.logger.warning(
            f'Failed to get client manifest from: "http://osu.{config.DOMAIN_NAME}/clients/manifest.json"'
        )
        return True

    return hash in manifest['hashes']
