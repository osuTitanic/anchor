
from __future__ import annotations

from app.common.constants import ANCHOR_WEB_RESPONSE
from app.clients.osu import OsuClient
from app.common.helpers import ip
from app.tasks import logins

from twisted.python.failure import Failure
from twisted.web.resource import Resource
from twisted.web.http import Request
from twisted.web import server
from queue import Queue

import config
import uuid
import app

class HttpOsuClient(OsuClient):
    def __init__(self, address: str, port: int) -> None:
        super().__init__(address, port)
        self.protocol = 'http'
        self.queue = Queue()
        self.token = ""

    @property
    def connected(self) -> bool:
        return self.token != ""

    def enqueue_packet(self, packet, *args):
        data = self.io.write_packet_to_bytes(packet, *args)
        self.logger.debug(f'<- "{packet.name}": {list(args)}')
        self.enqueue(data)

    def enqueue(self, data: bytes):
        self.queue.put(data)

    def dequeue(self) -> bytes:
        data = b""

        while not self.queue.empty():
            data += self.queue.get()

        return data

    def on_login_received(
        self,
        username: str,
        password: str,
        client_data: str
    ) -> None:
        self.token = str(uuid.uuid4())
        super().on_login_received(username, password, client_data)

        if not self.logged_in:
            self.token = ""

    def close_connection(self, reason: str = "") -> None:
        super().close_connection(reason)
        self.token = ""

class HttpOsuHandler(Resource):
    isLeaf = True

    def handle_login_request(self, request: Request):
        d = logins.manager.submit(self.process_login, request)
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

        try:
            username, password, client_data = (
                login_data.decode().splitlines()
            )

            player = HttpOsuClient(
                ip.resolve_ip_address_twisted(request),
                request.getClientAddress().port
            )

            player.on_login_received(
                username,
                password,
                client_data
            )
        except Exception as e:
            player.logger.error(f'Failed to process login: {e}', exc_info=e)
            player.close_connection('Login failure')
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

        request.setHeader('connection', 'keep-alive')
        request.write(result)
        request.finish()

    def on_login_error(self, failure: Failure, request: Request) -> None:
        app.session.logger.error(
            f'Failed to process login: {failure.getErrorMessage()}',
            exc_info=failure.value
        )

        if request.finished or request._disconnected:
            return

        response_data = self.server_error_packet()
        request.setHeader('connection', 'close')
        request.setResponseCode(500)
        request.write(response_data)
        request.finish()

    def handle_request(self, player: HttpOsuClient, request: Request):
        d = app.session.tasks.defer_to_reactor_thread(self.process_request, player, request)
        d.addErrback(self.on_request_error, player, request)
        d.addCallback(self.on_request_success, request)
        return server.NOT_DONE_YET

    def process_request(self, player: HttpOsuClient, request: Request) -> bytes:
        packets = player.io.read_many_packets_from_bytes(request.content.read())

        for packet, data in packets:
            player.on_packet_received(packet, data)

        return player.dequeue()

    def on_request_success(self, result: bytes, request: Request) -> None:
        if request.finished or request._disconnected:
            return

        request.setHeader('connection', 'keep-alive')
        request.write(result)
        request.finish()

    def on_request_error(self, failure: Failure, player: HttpOsuClient, request: Request) -> None:
        player.logger.error(f'Failed to process request: {failure.getErrorMessage()}', exc_info=failure.value)
        player.close_connection('Request processing error')

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
        request.setHeader('connection', 'close')
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
