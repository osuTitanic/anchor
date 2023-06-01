
from twisted.internet import reactor

from bancho.objects.ip import IPAddress
from bancho import BanchoFactory

import bancho
import config
import os

def setup():
    os.makedirs('.data', exist_ok=True)

    if not config.IP_DATABASE_URL:
        return

    if not os.path.isfile('./.data/geolite.mmdb'):
        IPAddress.download_gopip_database()

def main():
    factory = BanchoFactory()

    setup()

    for port in config.PORTS:
        reactor.listenTCP(port, factory)
        bancho.services.logger.info(f'Reactor listening on port: {port}')

    reactor.run()

if __name__ == "__main__":
    main()
