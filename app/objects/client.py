
from app.common.constants import OSU_VERSION
from app.common.helpers import location

from datetime import datetime
from typing import Optional

import hashlib
import utils
import pytz
import app
import re

class ClientVersion:
    def __init__(self, match: re.Match, date: int, revision: Optional[int] = None, stream: Optional[str] = None, name: Optional[str] = None) -> None:
        self.revision = revision
        self.stream   = stream
        self.match    = match
        self.date     = date
        self.name     = name

    def __repr__(self) -> str:
        return self.string

    @property
    def string(self) -> str:
        return self.match.string

    @classmethod
    def from_string(cls, string: str):
        match = OSU_VERSION.match(string)

        assert match is not None

        date = match.group('date')
        revision = match.group('revision')
        stream = match.group('stream')
        name = match.group('name')

        return ClientVersion(
            match,
            int(date),
            int(revision) if revision else None,
            stream,
            name
        )

class ClientHash:
    def __init__(self, md5: str, adapters: str, adapters_md5: str, uninstall_id: str, diskdrive_signature: str) -> None:
        self.diskdrive_signature = diskdrive_signature
        self.uninstall_id = uninstall_id
        self.adapters_md5 = adapters_md5
        self.adapters = adapters
        self.md5 = md5

    def __repr__(self) -> str:
        return self.string

    @property
    def string(self) -> str:
        return f'{self.md5}:{self.adapters}:{self.adapters_md5}:{self.uninstall_id}:{self.diskdrive_signature}'

    @classmethod
    def from_string(cls, string: str):
        try:
            md5, adapters, adapters_md5, uninstall_id, diskdrive_signature = string.split(':')
        except ValueError:
            args = string.split(':')

            md5 = args[0]
            adapters = args[1]
            adapters_md5 = args[2]

            diskdrive_signature = hashlib.md5(b'unknown').hexdigest()
            uninstall_id = hashlib.md5(b'unknown').hexdigest()

            try:
                uninstall_id = args[3]
                diskdrive_signature = args[4]
            except IndexError:
                pass

        return ClientHash(
            md5,
            adapters,
            adapters_md5,
            uninstall_id,
            diskdrive_signature
        )

class OsuClient:
    def __init__(self, ip: location.Geolocation, version: ClientVersion, client_hash: ClientHash, utc_offset: int, display_city: bool, friendonly_dms: bool) -> None:
        self.ip = ip
        self.hash = client_hash
        self.version = version
        self.utc_offset = utc_offset
        self.display_city = display_city
        self.friendonly_dms = friendonly_dms

    @classmethod
    def from_string(cls, line: str, ip: str):
        try:
            build_version, utc_offset, display_city, client_hash, friendonly_dms = line.split('|')
        except ValueError:
            # Workaround for older clients
            build_version, utc_offset, display_city, client_hash = line.split('|')
            friendonly_dms = False

        if not (geolocation := app.session.geolocation_cache.get(ip)):
            geolocation = location.fetch_geolocation(
                ip=ip,
                is_local=utils.is_local_ip(ip)
            )

            # Load ip geolocation from web and store to cache
            app.session.executor.submit(utils.load_geolocation_web, ip)

        utc_offset = int(
            datetime.now(
                pytz.timezone(geolocation.timezone)
            ).utcoffset().total_seconds() / 60 / 60
        )

        return OsuClient(
            geolocation,
            ClientVersion.from_string(build_version),
            ClientHash.from_string(client_hash),
            utc_offset,
            display_city = display_city == "1",
            friendonly_dms = friendonly_dms == "1"
        )

    @classmethod
    def empty(cls):
        return OsuClient(
            location.fetch_geolocation('127.0.0.1', True),
            ClientVersion(OSU_VERSION.match('b1337'), 1337),
            ClientHash('', '', '', '', ''),
            0,
            True,
            False
        )
