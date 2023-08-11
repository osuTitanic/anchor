
"""
This is protocol version 13, which is used from b20121223 to b20121203.
"""

from ..packets import PACKETS
from copy import deepcopy

# Inherit packets from 20130329
PACKETS[20121223] = deepcopy(PACKETS[20130329])
PACKETS[20121203] = deepcopy(PACKETS[20130329])
