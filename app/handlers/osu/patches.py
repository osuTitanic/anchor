
from typing import Tuple, Any, List
from copy import copy

from chio.clients import b20150915, b334
from chio.io import *
from chio import *

import config
import time
import app
import os

# Disable the compression to avoid issues with clients
# such as oldsu!, that just ignores it.
b334.disable_compression = True

# To make testing chio easier, we want to log all sorts of
# request packets the client sends to the server.
def log_incoming_packet(version: int, packet: str, data: bytes) -> None:
    if not data:
        return

    filename = f'{packet}_{int(time.time())}.bin'
    folder = f'{config.DATA_PATH}/packets/{version}/'
    filepath = os.path.join(folder, filename)
    os.makedirs(folder, exist_ok=True)

    with open(filepath, 'wb') as f:
        f.write(data)
        
@classmethod
def read_packet(cls, stream: Stream) -> Tuple[PacketType, Any]:
    packet_id = read_u16(stream)
    packet = cls.convert_input_packet(packet_id)

    if not packet.is_client_packet:
        raise ValueError(f"Packet '{packet.name}' is not a client packet")

    packet_reader = getattr(cls, packet.handler_name, None)

    if not packet_reader:
        raise NotImplementedError(f"Version '{cls.version}' does not implement packet '{packet.name}'")

    compression = read_boolean(stream)
    packet_length = read_u32(stream)
    packet_data = stream.read(packet_length)

    if compression:
        packet_data = decompress(packet_data)

    app.session.tasks.do_later(
        log_incoming_packet,
        cls.version, packet.name, packet_data
    )

    return packet, packet_reader(MemoryStream(packet_data))

# Apply the reader patch
b334.read_packet = read_packet

# This is a "hack" to get 16-player matches working
# by making the remaining slots locked.
def adjust_slot_size(match: Match) -> List[MatchSlot]:
    # Limit slots to max slots
    slots = match.slots[:config.MULTIPLAYER_MAX_SLOTS]

    if len(slots) < config.MULTIPLAYER_MAX_SLOTS:
        # Not enough slots -> fill empty slots
        remaining_slots = config.MULTIPLAYER_MAX_SLOTS - len(slots)

        for _ in range(remaining_slots):
            slot = MatchSlot(status=SlotStatus.Locked)
            slots.append(slot)
    return slots

@classmethod
def write_match(cls, output: Match) -> bytes:
    match = copy(output)
    match.slots = copy(match.slots)
    match.slots += (
        [MatchSlot(status=SlotStatus.Locked)] *
        max(cls.slot_size - config.MULTIPLAYER_MAX_SLOTS, 0)
    )

    stream = MemoryStream()
    write_u16(stream, match.id)
    write_boolean(stream, match.in_progress)
    write_u8(stream, match.type)
    write_u32(stream, match.mods.value)
    write_string(stream, match.name)
    write_string(stream, match.password)
    write_string(stream, match.beatmap_text)
    write_s32(stream, match.beatmap_id)
    write_string(stream, match.beatmap_checksum)

    for slot in match.slots:
        write_u8(stream, slot.status.value)

    for slot in match.slots:
        write_u8(stream, slot.team)

    for slot in match.slots:
        if slot.has_player:
            write_s32(stream, slot.user_id)

    write_s32(stream, match.host_id)
    write_u8(stream, match.mode)
    write_u8(stream, match.scoring_type)
    write_u8(stream, match.team_type)

    if cls.protocol_version >= 16:
        write_boolean(stream, match.freemod)

    if match.freemod:
        for slot in match.slots:
            write_u32(stream, slot.mods)

    if cls.protocol_version >= 18:
        write_u32(stream, match.seed)

    return stream.data

@classmethod
def read_match(cls, stream: MemoryStream) -> Match:
    match = Match()
    match.id = read_u16(stream)
    match.in_progress = read_boolean(stream)
    match.type = MatchType(read_u8(stream))
    match.mods = Mods(read_u32(stream))
    match.name = read_string(stream)
    match.password = read_string(stream)
    match.beatmap_text = read_string(stream)
    match.beatmap_id = read_s32(stream)
    match.beatmap_checksum = read_string(stream)
    match.slots = [
        MatchSlot(status=SlotStatus(read_u8(stream)))
        for _ in range(cls.slot_size)
    ]

    for slot in match.slots:
        slot.team = SlotTeam(read_u8(stream))

    for slot in match.slots:
        if slot.has_player:
            slot.user_id = read_s32(stream)

    match.host_id = read_s32(stream)
    match.mode = Mode(read_u8(stream))
    match.scoring_type = ScoringType(read_u8(stream))
    match.team_type = TeamType(read_u8(stream))

    if cls.protocol_version >= 16:
        match.freemod = read_boolean(stream)

    if match.freemod:
        for slot in match.slots:
            slot.mods = Mods(read_u32(stream))

    if cls.protocol_version >= 18:
        match.seed = read_u32(stream)

    match.slots = adjust_slot_size(match)
    return match

if config.MULTIPLAYER_MAX_SLOTS == 8:
    b20150915.read_match = read_match
    b20150915.write_match = write_match
