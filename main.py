
from twisted.internet import reactor

from app.logging import Console, File, Discord
from app.server import BanchoFactory

import logging
import config
import utils
import app

logging.basicConfig(
    handlers=[Console, File, Discord],
    level=logging.DEBUG
        if config.DEBUG
        else logging.INFO
)

def main():
    utils.setup()

    factory = BanchoFactory()

    for port in config.PORTS:
        reactor.listenTCP(port, factory)
        app.session.logger.info(
            f'Reactor listening on port: {port}'
        )

    reactor.run()

if __name__ == "__main__":
    main()
