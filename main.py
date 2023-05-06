
from twisted.internet import reactor
from bancho import BanchoFactory

import bancho
import config

def main():
    factory = BanchoFactory()

    for port in config.PORTS:
        reactor.listenTCP(port, factory)
        bancho.services.logger.info(f'Reactor listening on port: {port}')

    reactor.run()

if __name__ == "__main__":
    main()
