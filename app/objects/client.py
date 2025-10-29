
from app.common.constants import OSU_VERSION
from app.common.helpers import location
from datetime import datetime

import hashlib
import pytz
import re

class ClientVersion:
    def __init__(
        self,
        match: re.Match,
        date: int,
        revision: int | None = None,
        stream: str | None = None,
        name: str | None = None
    ) -> None:
        self.revision = revision
        self.stream = stream
        self.match = match
        self.date = date
        self.name = name

    def __repr__(self) -> str:
        return self.string

    @property
    def string(self) -> str:
        return self.match.string

    @property
    def identifier(self) -> str:
        return self.stream or self.name or 'stable'

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
    def __init__(
        self,
        md5: str,
        adapters: str,
        adapters_md5: str,
        uninstall_id: str,
        diskdrive_signature: str
    ) -> None:
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

    @property
    def unknown_hardware_ids(self) -> bool:
        return (
            self.diskdrive_signature == 'ad921d60486366258809553a3db49a4a' or
            self.uninstall_id == 'ad921d60486366258809553a3db49a4a'
        )

    @property
    def device_id(self) -> str:
        return hashlib.sha1(
            ':'.join([
                self.adapters_md5,
                self.uninstall_id,
                self.diskdrive_signature
            ]).encode()
        ).hexdigest()

    @classmethod
    def empty(cls, build_version: str):
        return ClientHash(
            md5=hashlib.md5(build_version.encode()).hexdigest(),
            adapters='',
            adapters_md5=hashlib.md5(b'').hexdigest(),
            uninstall_id=hashlib.md5(b'unknown').hexdigest(),
            diskdrive_signature=hashlib.md5(b'unknown').hexdigest()
        )

    @classmethod
    def from_string(cls, string: str):
        try:
            md5, adapters, adapters_md5, uninstall_id, diskdrive_signature = string.split(':')
        except ValueError:
            args = string.split(':')

            md5 = args[0]
            adapters = args[1]
            adapters_md5 = args[2]

            # Hardware IDs are not implemented
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

class OsuClientInformation:
    def __init__(
        self,
        version: ClientVersion,
        client_hash: ClientHash,
        utc_offset: int,
        display_city: bool,
        friendonly_dms: bool,
        protocol_version: int | None = None
    ) -> None:
        self.protocol_version = protocol_version or version.date
        self.friendonly_dms = friendonly_dms
        self.display_city = display_city
        self.utc_offset = utc_offset
        self.version = version
        self.hash = client_hash

    @property
    def is_wine(self) -> bool:
        return self.hash.adapters == 'runningunderwine'

    @property
    def supports_client_hash(self) -> bool:
        return self.version.date >= 1661

    @classmethod
    def from_string(cls, line: str) -> "OsuClientInformation":
        if len(args := line.split('|')) < 2:
            return None

        # Sent in every client version
        build_version = args[0]
        utc_offset = int(args[1])
        custom_protocol_version = None

        # Not sent in every client version
        client_hash = ClientHash.empty(build_version).string
        friendonly_dms = '0'
        display_city = '0'

        try:
            display_city = args[2]
            client_hash = args[3]
            friendonly_dms = args[4]
        except (ValueError, IndexError):
            pass

        if len(args) > 5 and args[5].isdigit():
            # Modded clients can specify a custom protocol
            # version to make use of newer features - this
            # is not a feature on the official clients
            custom_protocol_version = int(args[5])

        try:
            return OsuClientInformation(
                ClientVersion.from_string(build_version),
                ClientHash.from_string(client_hash),
                utc_offset,
                display_city=display_city == "1",
                friendonly_dms=friendonly_dms == "1",
                protocol_version=custom_protocol_version
            )
        except (ValueError, TypeError, IndexError):
            pass

    @classmethod
    def empty(cls) -> "OsuClientInformation":
        return OsuClientInformation(
            ClientVersion(OSU_VERSION.match('b0'), 0),
            ClientHash.empty('b0'),
            0, False, False
        )
