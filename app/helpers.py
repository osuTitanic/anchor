
from typing import Any, Iterable
from chio import PacketType

def enqueue_packet_cached(clients: Iterable[Any], packet: PacketType, *args) -> None:
    """Encode one packet per BanchoIO version and enqueue it to all clients."""
    data_cache = {}

    for client in clients:
        enqueue = getattr(client, "enqueue", None)

        if enqueue is None:
            # We can't enqueue to this client
            continue

        data = data_cache.get(client.io.version)

        if data is None:
            data = client.io.write_packet_to_bytes(packet, *args)
            data_cache[client.io.version] = data

        enqueue(data)
