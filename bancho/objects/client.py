
from typing import Optional

from .ip import IPAddress

class ClientVersion:
    def __init__(self, stream: str, date: int, subversion: Optional[str] = None) -> None:
        self.subversion = subversion
        self.stream     = stream
        self.date       = date

    @property
    def string(self) -> str:
        return f'{self.stream}{self.date}{self.subversion}'
    
    @classmethod
    def from_string(cls, string: str):
        stream = string[:1]
        version = string[1:].split('.')

        date = int(version[0])
        subversion = None

        if len(version) > 1:
            subversion = version[1]

        return ClientVersion(
            stream,
            date,
            subversion
        )

class OsuClient:
    def __init__(self, ip: IPAddress, version: ClientVersion, client_hash: str, utc_offset: int, display_city: bool, friendonly_dms: bool) -> None:
        self.ip = ip
        self.version = version
        self.utc_offset = utc_offset
        self.client_hash = client_hash
        self.display_city = display_city
        self.friendonly_dms = friendonly_dms

    @classmethod
    def from_string(cls, line: str, ip: str):
        build_version, utc_offset, display_city, client_hash, friendonly_dms = line.split('|')

        # TODO: Parse and validate client hash
        # TODO: Tournament clients

        return OsuClient(
            IPAddress(ip),
            ClientVersion.from_string(build_version),
            client_hash,
            int(utc_offset),
            display_city = display_city == "1",
            friendonly_dms = friendonly_dms == "1"
        )
    
    @classmethod
    def empty(cls):
        return OsuClient(
            IPAddress('127.0.0.1'),
            ClientVersion('b', 1337),
            '',
            0,
            True,
            False
        )


