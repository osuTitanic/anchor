
from twisted.python.failure import Failure
from twisted.web.http import Request

import config
import app

def thread_callback(error: Failure):
    app.session.logger.error(
        f'Failed to execute thread: {error.__str__()} ({error.getErrorMessage()})',
        exc_info=error.value
    )

def valid_client_hash(hash: str) -> bool:
    try:
        if not (manifest := app.session.client_manifest):
            response = app.session.requests.get(f'http://osu.{config.DOMAIN_NAME}/clients/manifest.json')

            if not response.ok:
                return True

            app.session.client_manifest = response.json()
            return valid_client_hash(hash)

    except ConnectionError:
        app.session.logger.warning(
            f'Failed to get client manifest from: "http://osu.{config.DOMAIN_NAME}/clients/manifest.json"'
        )
        return True

    return hash in manifest['hashes']

def resolve_ip_address(request: Request):
    if ip := request.requestHeaders.getRawHeaders("CF-Connecting-IP"):
        return ip[0]

    if forwards := request.requestHeaders.getRawHeaders("X-Forwarded-For"):
        return forwards[0]

    if ip := request.requestHeaders.getRawHeaders("X-Real-IP"):
        return ip[0]

    return request.getClientAddress().host.strip()
