
from twisted.internet import reactor

from bancho.objects.ip import IPAddress
from bancho.logging    import Console, File
from bancho            import BanchoFactory

import logging
import bancho
import config
import os

logging.basicConfig(
    handlers=[Console, File],
    level=logging.INFO
)

def setup():
    os.makedirs(config.DATA_PATH, exist_ok=True)

    if config.SKIP_IP_DATABASE:
        return

    if not os.path.isfile(f'{config.DATA_PATH}/geolite.mmdb'):
        IPAddress.download_gopip_database()

def main():
    factory = BanchoFactory()

    for port in config.PORTS:
        reactor.listenTCP(port, factory)
        bancho.services.logger.info(f'Reactor listening on port: {port}')

    reactor.run()

if __name__ == "__main__":
    setup()
    main()
