
from app.common.constants import ANCHOR_WEB_RESPONSE
from twisted.web.resource import Resource
from twisted.web.http import Request

class HttpBanchoProtocol(Resource):
    isLeaf = True

    def render_GET(self, request: Request):
        request.setHeader('Content-Type', 'text/html; charset=utf-8')
        return ANCHOR_WEB_RESPONSE.encode('utf-8')

    def render_POST(self, request: Request):
        ...
