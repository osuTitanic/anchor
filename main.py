
from twisted.internet import reactor
from bancho.services import factory as BanchoFactory

import bancho
import config

def main():
    for port in config.PORTS:
        reactor.listenTCP(port, BanchoFactory)
        bancho.services.logger.info(f'Reactor listening on port: {port}')

    reactor.run()

if __name__ == "__main__":
    main()
