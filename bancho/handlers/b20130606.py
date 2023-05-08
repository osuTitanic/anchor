
from typing import List, Tuple

from bancho.streams        import StreamIn, StreamOut
from bancho.common.objects import DBBeatmap
from bancho.constants      import (
    PresenceFilter,
    ResponsePacket,
    RequestPacket,
    ClientStatus,
    Permissions,
    Ranked,
    Grade,
    Mode,
    Mod
)

from . import BaseHandler

import threading
import bancho

class b20130606(BaseHandler):
    def enqueue_ping(self):
        self.player.sendPacket(ResponsePacket.PING)

    def enqueue_login_reply(self, response: int):
        self.player.sendPacket(
            ResponsePacket.LOGIN_REPLY,
            int(response).to_bytes(
                length=4,
                byteorder='little',
                signed=True
            )
        )

    def enqueue_announce(self, message: str):
        stream = StreamOut()
        stream.string(message)

        self.player.sendPacket(
            ResponsePacket.ANNOUNCE,
            stream.get()
        )

    def enqueue_privileges(self):
        self.player.sendPacket(
            ResponsePacket.LOGIN_PERMISSIONS,
            int(
                Permissions.pack(self.player.permissions)
            ).to_bytes(
                length=4,
                byteorder='little',
                signed=True
            )
        )

    def enqueue_message(self, sender, message: str, target_name: str):
        stream = StreamOut()

        stream.string(sender.name)
        stream.string(message)
        stream.string(target_name)
        stream.s32(sender.id)

        self.player.sendPacket(
            ResponsePacket.SEND_MESSAGE,
            stream.get()
        )

    def enqueue_channel(self, channel):
        stream = StreamOut()

        stream.string(channel.display_name)
        stream.string(channel.topic)
        stream.u16(channel.user_count)

        self.player.sendPacket(
            ResponsePacket.CHANNEL_AVAILABLE,
            stream.get()
        )

    def enqueue_channel_info_end(self):
        self.player.sendPacket(
            ResponsePacket.CHANNEL_INFO_COMPLETE
        )

    def enqueue_silence_info(self, remaining_silence: int):
        self.player.sendPacket(
            ResponsePacket.SILENCE_INFO,
            int(remaining_silence).to_bytes(
                length=4,
                byteorder='little',
                signed=True
            )
        )

    def enqueue_friends(self):
        stream = StreamOut()
        stream.intlist(self.player.friends)

        self.player.sendPacket(
            ResponsePacket.FRIENDS_LIST,
            stream.get()
        )

    def enqueue_presence(self, player):
        if self.player.filter == PresenceFilter.NoPlayers:
            return
        
        if self.player.filter == PresenceFilter.Friends:
            if player.id not in self.player.friends:
                return

        stream = StreamOut()

        stream.s32(player.id)
        stream.string(player.name)
        stream.u8(player.client.utc_offset + 24)
        stream.u8(player.client.ip.country_num)
        stream.u8((Permissions.pack(player.permissions) | (player.status.mode.value << 5)))
        stream.float(player.client.ip.longitude)
        stream.float(player.client.ip.latitude)
        stream.u32(player.current_stats.rank)

        self.player.sendPacket(
            ResponsePacket.USER_PRESENCE,
            stream.get()
        )

    def enqueue_stats(self, player):
        if not player:
            return

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
        stream.u32(sum([mod.value for mod in player.status.mods]))
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

    def enqueue_players(self, players):
        n = max(1, 32000)

        # Split players into chunks to avoid any buffer overflows
        for chunk in (players[i:i+n] for i in range(0, len(players), n)):
            stream = StreamOut()
            stream.intlist([p.id for p in chunk if p != self.player])
            self.player.sendPacket(
                ResponsePacket.USER_PRESENCE_BUNDLE,
                stream.get()
            )
        
    def enqueue_channel_revoked(self, target):
        stream = StreamOut()
        stream.string(target)

        self.player.sendPacket(
            ResponsePacket.CHANNEL_REVOKED,
            stream.get()
        )

    def enqueue_exit(self, player):
        stream = StreamOut()
        stream.s32(player.id)
        stream.u8(0) # Quit State (Only useful for irc)

        self.player.sendPacket(
            ResponsePacket.USER_QUIT,
            stream.get()
        )

    def enqueue_player(self, player):
        self.player.sendPacket(
            ResponsePacket.USER_PRESENCE_SINGLE,
            int(player.id).to_bytes(4, 'little')
        )

    def enqueue_beatmaps(self, beatmaps: List[Tuple[int, DBBeatmap]]):
        stream = StreamOut()
        stream.s32(len(beatmaps))

        for index, beatmap in beatmaps:
            personal_best = bancho.services.database.personal_best(beatmap.id, self.player.id)

            stream.s16(-1) # NOTE: We could use the index here, but I like it better this way
            stream.s32(beatmap.id)
            stream.s32(beatmap.set_id)
            stream.s32(beatmap.set_id) # TODO: Thread ID
            stream.u8(Ranked.from_status(beatmap.status).value)

            if not personal_best:
                stream.u8(Grade.N.value)
                stream.u8(Grade.N.value)
                stream.u8(Grade.N.value)
                stream.u8(Grade.N.value)
            else:
                stream.u8(Grade(personal_best.grade).value if personal_best.mode == 0 else 9)
                stream.u8(Grade(personal_best.grade).value if personal_best.mode == 1 else 9)
                stream.u8(Grade(personal_best.grade).value if personal_best.mode == 2 else 9)
                stream.u8(Grade(personal_best.grade).value if personal_best.mode == 3 else 9)

            stream.string(beatmap.md5)

        self.player.sendPacket(
            ResponsePacket.BEATMAP_INFO_REPLY,
            stream.get()
        )

    def enqueue_spectator(self, player):
        self.player.sendPacket(
            ResponsePacket.SPECTATOR_JOINED,
            int(player.id).to_bytes(4, 'little')
        )

    def enqueue_spectator_left(self, player):
        self.player.sendPacket(
            ResponsePacket.SPECTATOR_LEFT,
            int(player.id).to_bytes(4, 'little')
        )
    
    def enqueue_fellow_spectator(self, player):
        self.player.sendPacket(
            ResponsePacket.FELLOW_SPECTATOR_JOINED,
            int(player.id).to_bytes(4, 'little')
        )

    def enqueue_fellow_spectator_left(self, player):
        self.player.sendPacket(
            ResponsePacket.FELLOW_SPECTATOR_LEFT,
            int(player.id).to_bytes(4, 'little')
        )

    def enqueue_frames(self, frames: bytes):
        self.player.sendPacket(
            ResponsePacket.SPECTATE_FRAMES,
            frames
        )

    def enqueue_cant_spectate(self, player):
        self.player.sendPacket(
            ResponsePacket.CANT_SPECTATE,
            int(player.id).to_bytes(4, 'little')
        )

    def join_channel(self, name: str) -> bool:
        if not (channel := bancho.services.channels.by_name(name)):
            success = False
        else:
            success = channel.add(self.player)

        if name.startswith('#spec'):
            name = '#spectator'

        stream = StreamOut()
        stream.string(channel.display_name if success else name)

        if success:
            self.player.sendPacket(
                ResponsePacket.CHANNEL_JOIN_SUCCESS,
                stream.get()
            )
        else:
            self.player.sendPacket(
                ResponsePacket.CHANNEL_REVOKED,
                stream.get()
            )

        return success
    
    def leave_channel(self, name: str, kick=False):
        if not (channel := bancho.services.channels.by_name(name)):
            return
        
        try:
            channel.remove(self.player)
        except ValueError:
            pass

        if kick:
            self.enqueue_channel_revoked(channel.display_name)

    def handle_change_status(self, stream: StreamIn):
        # Check previous status
        if self.player.status.action == ClientStatus.Submitting:
            # Update stats on submit
            threading.Timer(
                function=self.player.update,
                interval=1
            ).start()

        # Update to new status
        self.player.status.action   = ClientStatus(stream.s8())
        self.player.status.text     = stream.string()
        self.player.status.checksum = stream.string()
        self.player.status.mods     = Mod.list(stream.u32())
        self.player.status.mode     = Mode(stream.u8())
        self.player.status.beatmap  = stream.s32()

        # Enqueue to other clients
        bancho.services.players.enqueue_stats(self.player)

    def handle_send_message(self, stream: StreamIn):
        sender    = stream.string()
        message   = stream.string()
        target    = stream.string()
        sender_id = stream.s32()

        if target.startswith('#multiplayer'):
            # TODO
            pass

        if target.startswith('#spectator'):
            if self.player.spectating:
                target = f'#spec_{self.player.spectating.id}'
            
            elif self.player.spectators:
                target = f'#spec_{self.player.id}'

            else:
                return

        if not (channel := bancho.services.channels.by_name(target)):
            return
        
        # TODO: Commands
        
        channel.send_message(self.player, message)

    def handle_send_private_message(self, stream: StreamIn):
        sender    = stream.string()
        message   = stream.string()
        target    = stream.string()
        sender_id = stream.s32()

        if not (player := bancho.services.players.by_name(target)):
            self.enqueue_channel_revoked(target)

        if self.player.silenced:
            return

        if player.silenced:
            return

        if player.client.friendonly_dms and Permissions.Admin not in self.player.permissions:
            stream = StreamOut()
            stream.string('')
            stream.string('')
            stream.string(player.name)
            stream.s32(-1)

            self.player.sendPacket(
                ResponsePacket.USER_DM_BLOCKED,
                stream.get()
            )
            return

        if len(message) > 127:
            message = message[:124] + '...'

        if player.status.action == ClientStatus.Afk and player.away_message:
            self.enqueue_message(player, player.away_message, target)

        # TODO: Commands

        player.handler.enqueue_message(
            self.player,
            message,
            self.player.name
        )

    def handle_exit(self, stream: StreamIn):
        update_avaliable = stream.bool()

    def handle_request_status(self, stream: StreamIn):
        self.enqueue_stats(self.player)

    def handle_join_lobby(self, stream: StreamIn):
        # TODO: Bancho_Lobbyjoin
        self.player.in_lobby = True

    def handle_part_lobby(self, stream: StreamIn):
        # TODO: Bancho_Lobbypart
        self.player.in_lobby = False

    def handle_join_channel(self, stream: StreamIn):
        name = stream.string()

        if name.startswith('#spectator'):
            if self.player.spectating:
                name = f'#spec_{self.player.spectating.id}'
            
            elif self.player.spectators:
                name = f'#spec_{self.player.id}'

            else:
                return

        self.join_channel(name)

    def handle_leave_channel(self, stream: StreamIn):
        name = stream.string()

        if name.startswith('#spectator'):
            if self.player.spectating:
                name = f'#spec_{self.player.spectating.id}'
            
            elif self.player.spectators:
                name = f'#spec_{self.player.id}'

            else:
                return

        self.leave_channel(name)

    def handle_receive_updates(self, stream: StreamIn):
        self.player.filter = PresenceFilter(stream.u32())

        self.enqueue_players(bancho.services.players)

    def handle_stats_request(self, stream: StreamIn):
        if self.player.restricted:
            return

        players = [bancho.services.players.by_id(id) for id in stream.intlist()]

        for player in players:
            self.enqueue_stats(player)

    def handle_presence_request(self, stream: StreamIn):
        if self.player.restricted:
            return

        players = [bancho.services.players.by_id(id) for id in stream.intlist()]

        for player in players:
            self.enqueue_presence(player)

    def handle_presence_request_all(self, stream: StreamIn):
        self.enqueue_players(bancho.services.players)

    def handle_add_friend(self, stream: StreamIn):
        if not (target := bancho.services.players.by_id(stream.s32())):
            return
        
        if target.id in self.player.friends:
            return
        
        bancho.services.database.add_relationship(
            self.player.id,
            target.id,
            friend=True
        )
        
        # Reload relationships
        self.player.reload_object()

        # Enqueue friends to client
        self.enqueue_friends()

    def handle_remove_friend(self, stream: StreamIn):
        if not (target := bancho.services.players.by_id(stream.s32())):
            return

        if target.id not in self.player.friends:
            return

        bancho.services.database.remove_relationship(
            self.player.id,
            target.id
        )

        # Reload relationships
        self.player.reload_object()

        # Enqueue friends to client
        self.enqueue_friends()

    def handle_set_away_message(self, stream: StreamIn):
        sender                   = stream.string()
        self.player.away_message = stream.string()
        target                   = stream.string()
        sender_id                = stream.s32()

    def handle_change_friendonly_dms(self, stream: StreamIn):
        self.player.client.friendonly_dms = bool(stream.s32())

    def handle_beatmap_info(self, stream: StreamIn):
        beatmaps: List[Tuple[int, DBBeatmap]] = []

        for index in range(stream.s32()):
            # Filenames
            if not (beatmap := bancho.services.database.beatmap_by_file(stream.string())):
                continue

            beatmaps.append((
                index,
                beatmap
            ))

        self.enqueue_beatmaps(beatmaps)

    def handle_start_spectating(self, stream: StreamIn):
        if self.player.restricted:
            return
        
        if not (target := bancho.services.players.by_id(stream.s32())):
            return
        
        self.player.spectating = target

        # Join their channel
        self.enqueue_channel(target.spectator_channel)
        self.join_channel(f'#spec_{target.id}')

        # Enqueue to other spectators
        for p in target.spectators:
            p.handler.enqueue_fellow_spectator(self.player)

        target.spectators.append(self.player)

        target.handler.enqueue_spectator(self.player)
        target.handler.enqueue_channel(target.spectator_channel)

        if target not in target.spectator_channel.users:
            target.handler.join_channel(f'#spec_{target.id}')

    def handle_stop_spectating(self, stream: StreamIn):
        if self.player.restricted:
            return

        # Leave spectator channel        
        self.leave_channel(
            '#spectator', kick=True
        )

        self.player.spectating.spectators.remove(self.player)

        # Enqueue to other spectators
        for p in self.player.spectating.spectators:
            p.handler.enqueue_fellow_spectator_left(self.player)

        # Enqueue to target
        self.player.spectating.handler.enqueue_spectator_left(self.player)

        # If target has no spectators anymore
        # kick them from the spectator channel
        if not self.player.spectating.spectators:
            self.player.spectating.handler.leave_channel(
                '#spectator', kick=True
            )

        self.player.spectating = None

    def handle_send_frames(self, stream: StreamIn):
        if self.player.restricted:
            return
        
        for p in self.player.spectators:
            p.handler.enqueue_frames(stream.readall())

    def handle_cant_spectate(self, stream: StreamIn):
        if self.player.restricted:
            return
        
        if not self.player.spectating:
            return
        
        self.player.spectating.handler.enqueue_cant_spectate(self.player)

        for p in self.player.spectating.spectators:
            p.handler.enqueue_cant_spectate(self.player)
