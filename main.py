
from twisted.internet import reactor
from bancho.services import factory as BanchoFactory

def main():
    reactor.listenTCP(13381, BanchoFactory)
    reactor.listenTCP(13382, BanchoFactory)
    reactor.run()

if __name__ == "__main__":
    main()
