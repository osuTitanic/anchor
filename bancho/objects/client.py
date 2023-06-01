
from typing import Optional

from .ip import IPAddress

class ClientVersion:
    def __init__(self, stream: str, date: int, subversion: Optional[str] = None) -> None:
        self.subversion = subversion
        self.stream     = stream
        self.date       = date
    
    def __repr__(self) -> str:
        return self.string        

    @property
    def string(self) -> str:
        return f'{self.stream}{self.date}{f".{self.subversion}" if self.subversion else ""}'
    
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
        md5, adapters, adapters_md5, uninstall_id, diskdrive_signature = string.split(':')

        return ClientHash(
            md5,
            adapters,
            adapters_md5,
            uninstall_id,
            diskdrive_signature
        )

class OsuClient:
    def __init__(self, ip: IPAddress, version: ClientVersion, client_hash: ClientHash, utc_offset: int, display_city: bool, friendonly_dms: bool) -> None:
        self.ip = ip
        self.hash = client_hash
        self.version = version
        self.utc_offset = utc_offset
        self.display_city = display_city
        self.friendonly_dms = friendonly_dms

    @classmethod
    def from_string(cls, line: str, ip: str):
        build_version, utc_offset, display_city, client_hash, friendonly_dms = line.split('|')

        return OsuClient(
            IPAddress(ip),
            ClientVersion.from_string(build_version),
            ClientHash.from_string(client_hash),
            int(utc_offset),
            display_city = display_city == "1",
            friendonly_dms = friendonly_dms == "1"
        )
    
    @classmethod
    def empty(cls):
        return OsuClient(
            IPAddress('127.0.0.1'),
            ClientVersion('b', 1337),
            ClientHash('', '', '', '', ''),
            0,
            True,
            False
        )


