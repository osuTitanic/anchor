
from __future__ import annotations
from typing import List

from app.common.constants import ANCHOR_WEB_RESPONSE
from app.common.streams import StreamIn
from app.objects.client import OsuClient
from app.objects.player import Player
from app.common.helpers import ip
from app.objects import OsuClient

from twisted.web.server import NOT_DONE_YET
from twisted.internet.error import ConnectionDone
from twisted.internet import threads, reactor
from twisted.python.failure import Failure
from twisted.web.resource import Resource
from twisted.web.http import Request
from queue import Queue

import config
import gzip
import uuid
import app

class HttpPlayer(Player):
    def __init__(self, address: str, port: int) -> None:
        super().__init__(address, port)
        self.protocol = 'http'
        self.queue = Queue()
        self.token = ""

    @property
    def connected(self) -> bool:
        return self.token != ""

    def enqueue(self, data: bytes):
        self.queue.put(data)

    def dequeue(self, max: int = 4096) -> bytes:
        data = b""

        while not self.queue.empty():
            data += self.queue.get()

            if len(data) > max:
                # Let client perform fast-read
                break

        return data

    def login_received(self, username: str, md5: str, client: OsuClient) -> None:
        super().login_received(
            username,
            md5,
            client
        )

        if self.logged_in:
            self.token = str(uuid.uuid4())

    def close_connection(self, error: Exception | None = None) -> None:
        if error:
            self.send_error()

        self.logger.info(f'Closing connection -> <{self.address}>')
        self.token = ""
        super().connectionLost(Failure(error or ConnectionDone()))

class HttpBanchoProtocol(Resource):
    isLeaf = True

    def __init__(self) -> None:
        self.player: HttpPlayer | None = None
        self.children = {}

    def handle_login_request(self, request: Request) -> bytes:
        request.setHeader('cho-token', '')

        if request.getHeader('User-Agent') != 'osu!':
            request.setResponseCode(403)
            return b''

        try:
            username, password, client_data = (
                request.content.read().decode().splitlines()
            )

            ip_address = ip.resolve_ip_address_twisted(request)

            self.player = HttpPlayer(
                ip_address,
                request.getClientAddress().port
            )

            self.player.client = OsuClient.from_string(
                client_data,
                ip_address
            )

            deferred = threads.deferToThread(
                self.player.login_received,
                username,
                password,
                self.player.client
            )

            deferred.addErrback(
                lambda f: self.on_request_error(request, f.value)
            )

            deferred.addCallback(
                lambda _: self.on_login_done(request)
            )
        except Exception as e:
            return self.on_request_error(
                request, e
            )

        return NOT_DONE_YET

    def handle_request(self, request: Request) -> bytes:
        deferred = threads.deferToThread(
            self.process_packets,
            request.content.read()
        )

        deferred.addErrback(
            lambda f: self.on_request_error(request, f.value)
        )

        deferred.addCallback(
            lambda _: self.on_request_done(request)
        )

        return NOT_DONE_YET

    def process_packets(self, content: bytes):
        stream = StreamIn(content)

        while not stream.eof():
            packet = stream.u16()
            compression = stream.bool()
            payload = stream.read(stream.u32())

            if compression:
                payload = gzip.decompress(payload)

            self.player.packet_received(
                packet_id=packet,
                stream=StreamIn(payload)
            )

    def on_request_done(self, request: Request) -> None:
        cf_country_header = request.getHeader('CF-IPCountry')

        if cf_country_header not in ('XX', 'T1', None):
            # Player is using a VPN or proxy
            self.player.client.ip.country_code = cf_country_header

        if request._disconnected:
            self.player.logger.warning('Client disconnected before response')
            return

        if request.finished:
            self.player.logger.warning('Request finished before response')
            return

        reactor.callFromThread(
            lambda: (
                request.write(self.player.dequeue()),
                request.finish()
            )
        )

    def on_request_error(
        self,
        request: Request,
        error: Exception
    ) -> None:
        request.setResponseCode(500)
        self.player.send_error()
        self.player.logger.error(
            f'Failed to process request: {error}',
            exc_info=error
        )
        self.on_request_done(request)

    def on_login_done(self, request: Request) -> None:
        request.setHeader('cho-token', self.player.token)
        self.on_request_done(request)

    def force_reconnect(self) -> bytes:
        """Force a client to reconnect, using the Restart packet."""
        return b'\x56\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00'

    def render_GET(self, request: Request) -> bytes:
        request.setHeader('content-type', 'text/html; charset=utf-8')
        request.setHeader('server', 'bancho')
        return ANCHOR_WEB_RESPONSE.encode('utf-8')

    def render_POST(self, request: Request) -> bytes:
        request.setHeader('server', 'bancho')
        request.setHeader('cho-protocol', '18')
        request.setResponseCode(200)

        if not (osu_token := request.getHeader('osu-token')):
            return self.handle_login_request(request)

        if not (player := app.session.players.by_token(osu_token)):
            # Tell client to reconnect immediately (restart packet)
            return self.force_reconnect()

        if not player.logged_in:
            request.setResponseCode(403)
            return b''

        self.player = player
        return self.handle_request(request)
