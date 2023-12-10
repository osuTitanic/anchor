
from typing import Dict, Callable, Optional
from dataclasses import dataclass, field
from copy import deepcopy

from .constants import PacketEnum
from .writer import BaseWriter
from .reader import BaseReader

@dataclass(slots=True)
class ClientVersion:
    version: int
    protocol_version: int
    request_packets: PacketEnum
    response_packets: PacketEnum
    decoders: Dict[PacketEnum, Callable] = field(default_factory=dict)
    encoders: Dict[PacketEnum, Callable] = field(default_factory=dict)

VERSIONS: Dict[int, ClientVersion] = {}

# TODO: Missing protocol versions:
#       16, 14, 9, 5

def register_version(
    version: int,
    protocol_version: int,
    response_packets: PacketEnum,
    request_packets: PacketEnum,
    inherit_from: Optional[int] = None
) -> ClientVersion:
    VERSIONS[version] = (
        cv := ClientVersion(
            version,
            protocol_version,
            request_packets,
            response_packets
        )
    )

    if inherit_from:
        cv.decoders = deepcopy(VERSIONS[inherit_from].decoders)
        cv.encoders = deepcopy(VERSIONS[inherit_from].encoders)

    return cv

def register_decoder(
    version: int,
    packet: PacketEnum,
    handler: Callable
) -> None:
    if version not in VERSIONS:
        raise ValueError('Version was not registered!')

    VERSIONS[version].decoders[packet] = handler

def register_encoder(
    version: int,
    packet: PacketEnum,
    handler: Callable
) -> None:
    if version not in VERSIONS:
        raise ValueError('Version was not registered!')

    VERSIONS[version].encoders[packet] = handler

def get_next_version(version: int) -> ClientVersion:
    ...
