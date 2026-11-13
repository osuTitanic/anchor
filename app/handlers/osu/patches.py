
from chio.clients import b334
from chio.io import *
from chio import *

# Disable the compression to avoid issues with clients
# such as oldsu!, that just ignores it.
b334.disable_compression = True
