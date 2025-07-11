
from config import SSL_CERTFILE, SSL_KEYFILE
from twisted.internet import reactor

def setup(min_protocol: int):
    try:
        from twisted.protocols import tls
        from twisted.internet import ssl as TwistedSSL
    except ImportError:
        return None

    context_factory = TwistedSSL.DefaultOpenSSLContextFactory(
        SSL_KEYFILE,
        SSL_CERTFILE
    )

    # Set minimum protocol version thats allowed
    context: TwistedSSL.SSL.Context = context_factory._context
    context.set_min_proto_version(min_protocol)

    # Make tls writes thread-safe
    tls.TLSMemoryBIOProtocol.write = lambda self, data: (
        reactor.callFromThread(tls.TLSMemoryBIOProtocol._write, self, data)
    )

    # Usually the protocol is set to `BufferingTLSTransport`, however
    # this protocol has proven to be very unreliable to use, especially
    # with sending smaller data. Sent packets would often just stay in
    # the buffer and not be dequeued until the next packet is sent.
    tls.TLSMemoryBIOFactory.protocol = tls.TLSMemoryBIOProtocol
    return context_factory

def listen(port, factory, context_factory, backlog=50, interface=''):
    return reactor.listenSSL(
        port,
        factory,
        context_factory,
        backlog=backlog,
        interface=interface
    )
