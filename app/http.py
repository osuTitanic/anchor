
from __future__ import annotations

from app.common.constants import ANCHOR_WEB_RESPONSE
from app.objects.client import OsuClient
from app.common.streams import StreamIn
from app.objects.player import Player
from app.common.helpers import ip
from app.objects import OsuClient

from twisted.internet.error import ConnectionDone
from twisted.python.failure import Failure
from twisted.web.resource import Resource
from twisted.web.http import Request
from twisted.internet import threads
from twisted.web import server
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
        super().login_received(username, md5, client)

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

    def handle_login_request(self, request: Request):
        d = threads.deferToThread(self.process_login, request)
        d.addCallback(self.on_login_success, request)
        d.addErrback(self.on_login_error, request)
        return server.NOT_DONE_YET

    def process_login(self, request: Request) -> bytes:
        login_data = request.content.read()

        if login_data.count(b'\n') < 3:
            request.setHeader('connection', 'close')
            request.setResponseCode(400)
            return b''

        app.session.logger.debug(
            f'-> Received login: {login_data}'
        )

        username, password, client_data = (
            login_data.decode().splitlines()
        )

        ip_address = ip.resolve_ip_address_twisted(request)

        player = HttpPlayer(
            ip_address,
            request.getClientAddress().port
        )

        client = OsuClient.from_string(
            client_data,
            ip_address
        )

        if not client:
            player.logger.warning(f'Failed to parse client: "{client_data}"')
            request.setHeader('connection', 'close')
            request.setResponseCode(400)
            return b''

        try:
            player.login_received(
                username,
                password,
                client
            )
        except Exception as e:
            player.logger.error(f'Failed to process login: {e}')
            player.close_connection(e)
            request.setHeader('connection', 'close')
            request.setResponseCode(500)

        request.setHeader(
            'cho-token',
            player.token
        )

        return player.dequeue()

    def on_login_success(self, result: bytes, request: Request) -> None:
        if request.finished or request._disconnected:
            return

        request.write(result)
        request.finish()

    def on_login_error(self, failure: Failure, request: Request) -> None:
        app.session.logger.error(
            f'Failed to process login: {failure.getErrorMessage()}'
        )

        if request.finished or request._disconnected:
            return

        response_data = self.server_error_packet()
        request.setHeader('connection', 'close')
        request.setResponseCode(500)
        request.write(response_data)
        request.finish()

    def handle_request(self, player: HttpPlayer, request: Request):
        d = threads.deferToThread(self.process_request, player, request)
        d.addErrback(self.on_request_error, player, request)
        d.addCallback(self.on_request_success, request)
        return server.NOT_DONE_YET

    def process_request(self, player: HttpPlayer, request: Request) -> bytes:
        stream = StreamIn(request.content.read())

        while not stream.eof():
            packet = stream.u16()
            compression = stream.bool()
            payload = stream.read(stream.u32())

            if compression:
                payload = gzip.decompress(payload)

            player.packet_received(
                packet_id=packet,
                stream=StreamIn(payload)
            )

        return player.dequeue()

    def on_request_success(self, result: bytes, request: Request) -> None:
        if request.finished or request._disconnected:
            return

        request.write(result)
        request.finish()

    def on_request_error(self, failure: Failure, player: HttpPlayer, request: Request) -> None:
        player.logger.error(f'Failed to process request: {failure.getErrorMessage()}')
        player.close_connection(failure.value)

        if request.finished or request._disconnected:
            return

        request.setHeader('connection', 'close')
        request.setResponseCode(500)
        request.write(player.dequeue())
        request.finish()

    def force_reconnect(self) -> bytes:
        """Force a client to reconnect, using the Restart packet."""
        return b'\x56\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00'

    def server_error_packet(self) -> bytes:
        """Tell the client something went really wrong."""
        return b'\x05\x00\x00\x04\x00\x00\x00\xfb\xff\xff\xff'

    def render_GET(self, request: Request):
        request.setHeader('content-type', 'text/html; charset=utf-8')
        request.setHeader('server', 'bancho')
        return ANCHOR_WEB_RESPONSE.encode('utf-8')

    def render_POST(self, request: Request):
        request.setHeader('cho-protocol', str(config.PROTOCOL_VERSION))
        request.setHeader('server', 'bancho')
        request.setResponseCode(200)

        if request.getHeader('User-Agent') != 'osu!':
            request.setHeader('connection', 'close')
            request.setResponseCode(403)
            return b''

        if not (osu_token := request.getHeader('osu-token')):
            return self.handle_login_request(request)

        if not (player := app.session.players.by_token(osu_token)):
            return self.force_reconnect()

        if not player.logged_in:
            request.setHeader('connection', 'close')
            request.setResponseCode(401)
            return b''

        return self.handle_request(player, request)
