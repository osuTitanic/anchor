
from bancho.constants import PresenceFilter, ResponsePacket
from bancho.streams import StreamOut, StreamIn
from bancho.common.objects import DBStats
from bancho.constants import (
    MatchScoringTypes,
    MatchTeamTypes,
    PresenceFilter,
    ResponsePacket,
    ClientStatus,
    SlotStatus,
    MatchType,
    SlotTeam,
    Mode,
    Mod
)

from .b20121030 import b20121030

import threading
import bancho

class b20120812(b20121030):
    
    protocol_version = 10

    def enqueue_stats(self, player, force=False):
        if not player:
            return

        if not force:
            if self.player.filter == PresenceFilter.NoPlayers:
                return

            if self.player.filter == PresenceFilter.Friends:
                if player.id not in self.player.friends:
                    return

        stream = StreamOut()
        stream.s32(player.id)

        # Status
        stream.u8(player.status.action.value)
        stream.string(player.status.text)
        stream.string(player.status.checksum)
        stream.u16(sum([mod.value for mod in player.status.mods]))
        stream.s8(player.status.mode.value)
        stream.s32(player.status.beatmap)

        # Stats
        stream.s64(player.current_stats.rscore)
        stream.float(player.current_stats.acc)
        stream.s32(player.current_stats.playcount)
        stream.s64(player.current_stats.tscore)
        stream.s32(player.current_stats.rank)
        stream.u16(round(player.current_stats.pp))

        self.player.sendPacket(
            ResponsePacket.USER_STATS,
            stream.get()
        )
    
    def read_match(self, stream: StreamIn):
        
        from ..objects.multiplayer import Match

        match_id = stream.s16()

        in_progress = stream.bool()
        match_type = MatchType(stream.u8())
        mods = Mod.list(stream.s16())

        name = stream.string()
        password = stream.string()

        beatmap_name = stream.string()
        beatmap_id   = stream.s32()
        beatmap_hash = stream.string()

        slot_status = [stream.u8()   for _ in range(8)]
        slot_team   = [stream.u8()   for _ in range(8)]
        slot_id     = [stream.s32()  for i in range(8) if slot_status[i] & SlotStatus.HasPlayer.value]

        host = bancho.services.players.by_id(stream.s32())
        mode = Mode(stream.u8())

        match_scoring_type = MatchScoringTypes(stream.u8())
        match_team_type    = MatchTeamTypes(stream.u8())

        freemod = False

        m = Match(
            match_id,
            name,
            password,
            host,
            beatmap_id,
            beatmap_name,
            beatmap_hash,
            mode
        )

        m.in_progress  = in_progress
        m.type         = match_type
        m.mods         = mods
        m.scoring_type = match_scoring_type
        m.team_type    = match_team_type
        m.freemod      = freemod

        for index, slot in enumerate(m.slots):
            slot.status = SlotStatus(slot_status[index])
            slot.team   = SlotTeam(slot_team[index])

        return m

    def write_match(self, match, stream: StreamOut, send_password: bool = False):
        stream.u16(match.id)
        stream.bool(match.in_progress)
        stream.u8(match.type.value)
        stream.u16(Mod.pack(match.mods))
        stream.string(match.name)

        if send_password:
            stream.string(match.password)
        else:
            if match.password:
                stream.write(b'\x0b\x00')
            else:
                stream.write(b'\x00')

        stream.string(match.beatmap_name)
        stream.s32(match.beatmap_id)
        stream.string(match.beatmap_hash)

        [stream.u8(slot.status.value) for slot in match.slots]
        [stream.u8(slot.team.value)   for slot in match.slots]
        [stream.s32(slot.player.id)   for slot in match.slots if slot.has_player]

        stream.s32(match.host.id)
        stream.u8(match.mode.value)
        stream.u8(match.scoring_type.value)
        stream.u8(match.team_type.value)

        return stream

    def handle_change_status(self, stream: StreamIn):
        # Update to new status
        self.player.status.action   = ClientStatus(stream.s8())
        self.player.status.text     = stream.string()
        self.player.status.checksum = stream.string()
        self.player.status.mods     = Mod.list(stream.u16())
        self.player.status.mode     = Mode(stream.u8())
        self.player.status.beatmap  = stream.s32()

        # Remove "FreeModAllowed"
        if Mod.FreeModAllowed in self.player.status.mods:
            self.player.status.mods.remove(Mod.FreeModAllowed)

        bancho.services.cache.update_user(self.player)

        self.player.logger.debug(f'Changed status: {self.player.status}')
        self.player.update_rank()

        # Enqueue to other players
        # (This needs to be done for older clients)
        bancho.services.players.enqueue_stats(self.player)
