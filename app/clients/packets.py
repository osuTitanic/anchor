
from typing import Dict, Callable, Tuple
from enum import Enum

PACKETS: Dict[
    int,
    Tuple[
        Dict[Enum, Callable], # RequestPackets
        Dict[Enum, Callable]  # ResponsePackets
    ]
] = {
    2013606: ({}, {})
    # Implement more clients here ...
}
