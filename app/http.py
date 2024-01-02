
from app.common.constants import ANCHOR_WEB_RESPONSE
from twisted.web.resource import Resource

class HttpBanchoProtocol(Resource):
    isLeaf = True

    def __init__(self, bancho):
        self.bancho = bancho

    def render_GET(self, request):
        request.setHeader('Content-Type', 'text/html; charset=utf-8')
        return ANCHOR_WEB_RESPONSE

    def render_POST(self, request):
        ...
