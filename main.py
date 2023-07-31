
from twisted.internet import reactor

from app.server import BanchoFactory
from app.logging import Console, File

import logging
import config
import app

logging.basicConfig(
    handlers=[Console, File],
    level=logging.INFO
)

def main():
    factory = BanchoFactory()

    for port in config.PORTS:
        reactor.listenTCP(port, factory)
        app.session.logger.info(
            f'Reactor listening on port: {port}'
        )

    reactor.run()

if __name__ == "__main__":
    main()
