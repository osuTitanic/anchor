
from app.common.constants import OSU_VERSION
from contextlib import suppress

import hashlib
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
    def is_empty(self) -> bool:
        return (
            self.empty_adapters and
            self.unknown_unique_ids
        )

    @property
    def empty_adapters(self) -> bool:
        return (
            self.adapters_md5 == 'd41d8cd98f00b204e9800998ecf8427e' and
            self.adapters == ''
        )

    @property
    def unknown_unique_ids(self) -> bool:
        return (
            self.diskdrive_signature == 'ad921d60486366258809553a3db49a4a' or
            self.uninstall_id == 'ad921d60486366258809553a3db49a4a'
        )

    @classmethod
    def from_string(cls, string: str):
        args = string.split(':')
        assert len(args) >= 3

        # Executable hash & mac addresses have to be present
        # starting from version b1661 and onwards
        md5 = args[0]
        adapters = args[1]
        adapters_md5 = args[2]

        # Hardware IDs are not always present, but
        # should be starting from b20120506 and onwards
        diskdrive_signature = hashlib.md5(b'unknown').hexdigest()
        uninstall_id = hashlib.md5(b'unknown').hexdigest()

        with suppress(IndexError):
            uninstall_id = args[3]
            diskdrive_signature = args[4]

        return ClientHash(
            md5,
            adapters,
            adapters_md5,
            uninstall_id,
            diskdrive_signature
        )

    @classmethod
    def empty(cls, build_version: str):
        return ClientHash(
            md5=hashlib.md5(build_version.encode()).hexdigest(),
            adapters='',
            adapters_md5=hashlib.md5(b'').hexdigest(),
            uninstall_id=hashlib.md5(b'unknown').hexdigest(),
            diskdrive_signature=hashlib.md5(b'unknown').hexdigest()
        )

class OsuClientInformation:
    def __init__(
        self,
        version: ClientVersion,
        client_hash: ClientHash,
        utc_offset: int = 0,
        display_city: bool = False,
        friendonly_dms: bool = False,
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

    @property
    def supports_unique_ids(self) -> bool:
        return self.version.date >= 20120506

    @classmethod
    def empty(cls) -> "OsuClientInformation":
        return OsuClientInformation(
            ClientVersion.from_string('b0'),
            ClientHash.empty('b0')
        )

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

        with suppress(ValueError, IndexError):
            display_city = args[2]
            client_hash = args[3]
            friendonly_dms = args[4]

        if len(args) > 5 and args[5].isdigit():
            # Modded clients can specify a custom protocol
            # version to make use of newer features - this
            # is not a feature on the official clients
            custom_protocol_version = int(args[5])

        with suppress(ValueError, TypeError, IndexError, AssertionError):
            return OsuClientInformation(
                ClientVersion.from_string(build_version),
                ClientHash.from_string(client_hash),
                utc_offset=utc_offset,
                display_city=display_city == "1",
                friendonly_dms=friendonly_dms == "1",
                protocol_version=custom_protocol_version
            )
