
from typing import List, Tuple, Optional

from bancho.streams             import StreamIn, StreamOut
from bancho.common.objects      import DBBeatmap
from bancho.objects.channel     import Channel
from bancho.constants           import (
    SPEED_MODS,
    MatchScoringTypes,
    MatchTeamTypes,
    PresenceFilter,
    ResponsePacket,
    ClientStatus,
    Permissions,
    SlotStatus,
    MatchType,
    SlotTeam,
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

    def enqueue_menu_icon(self, image: Optional[str], url: Optional[str]):
        stream = StreamOut()

        if not image:
            stream.string('')
        else:
            stream.string(
                '|'.join([
                    image,
                    url if url else ''
                ])
            )
        
        print(stream.get())

        self.player.sendPacket(
            ResponsePacket.MENU_ICON,
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
            
        utc = (
            player.client.ip.utc_offset 
            if player.client.ip.utc_offset 
            else player.client.utc_offset
        )

        stream = StreamOut()

        stream.s32(player.id)
        stream.string(player.name)
        stream.u8(utc + 24)
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
        self.player.logger.info(f'Spectator joined: {player.name}')
        self.player.sendPacket(
            ResponsePacket.SPECTATOR_JOINED,
            int(player.id).to_bytes(4, 'little')
        )

    def enqueue_spectator_left(self, player):
        self.player.logger.info(f'Spectator left: {player.name}')
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

    def enqueue_match(self, match, send_password=False, update=False):
        stream = StreamOut()

        self.write_match(match, stream, send_password)

        self.player.sendPacket(
            ResponsePacket.NEW_MATCH
            if not update else
            ResponsePacket.UPDATE_MATCH,
            stream.get()
        )

    def enqueue_match_disband(self, match_id: int):
        self.player.sendPacket(
            ResponsePacket.DISBAND_MATCH,
            int(match_id).to_bytes(4, 'little')
        )

    def enqueue_match_player_failed(self, slot_id: int):
        self.player.sendPacket(
            ResponsePacket.MATCH_PLAYER_FAILED,
            int(slot_id).to_bytes(4, 'little')
        )

    def enqueue_match_player_skipped(self, slot_id: int):
        self.player.sendPacket(
            ResponsePacket.MATCH_PLAYER_SKIPPED,
            int(slot_id).to_bytes(4, 'little')
        )

    def enqueue_match_all_players_loaded(self):
        self.player.sendPacket(ResponsePacket.MATCH_ALL_PLAYERS_LOADED)

    def enqueue_match_complete(self):
        self.player.sendPacket(ResponsePacket.MATCH_COMPLETE)

    def enqueue_match_transferhost(self):
        self.player.sendPacket(ResponsePacket.MATCH_TRANSFER_HOST)

    def enqueue_match_skip(self):
        self.player.sendPacket(ResponsePacket.MATCH_SKIP)

    def enqueue_matchjoin_success(self, match):
        stream = StreamOut()
        self.write_match(match, stream, send_password=True)

        self.player.sendPacket(
            ResponsePacket.MATCH_JOIN_SUCCESS,
            stream.get()
        )

    def enqueue_match_start(self, match):
        stream = StreamOut()
        self.write_match(
            match,
            stream
        )

        self.player.sendPacket(
            ResponsePacket.MATCH_START,
            stream.get()
        )

    def enqueue_matchjoin_fail(self):
        self.player.sendPacket(ResponsePacket.MATCH_JOIN_FAIL)

    def enqueue_lobby_join(self, user_id: int):
        for player in bancho.services.players.in_lobby:
            player.sendPacket(
                ResponsePacket.LOBBY_JOIN,
                int(user_id).to_bytes(4, 'little')
            )

    def enqueue_lobby_part(self, user_id: int):
        for player in bancho.services.players.in_lobby:
            player.sendPacket(
                ResponsePacket.LOBBY_PART,
                int(user_id).to_bytes(4, 'little')
            )

    def join_channel(self, name: str) -> bool:
        if not (channel := bancho.services.channels.by_name(name)):
            success = False
        else:
            success = channel.add(self.player)

        if name.startswith('#spec'):
            name = '#spectator'
        elif name.startswith('#multi'):
            name = '#multiplayer'

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

    def join_match(self, match, password: str) -> bool:
        if self.player.restricted:
            return False
        
        if self.player.match:
            self.enqueue_matchjoin_fail()
            return False

        if self is not match.host:
            if password != match.password and Permissions.Admin not in self.player.permissions:
                # Invalid password
                self.enqueue_matchjoin_fail()
                return False
            
            if (slot_id := match.get_free()) is None:
                # Match is full
                self.enqueue_matchjoin_fail()
                return False
        else:
            # Player is creating a match
            slot_id = 0

        if not self.join_channel(match.chat.name):
            self.enqueue_matchjoin_fail()
            return False

        self.leave_channel('#lobby')

        slot = match.slots[0 if slot_id == -1 else slot_id]

        if match.team_type in (MatchTeamTypes.TeamVs, MatchTeamTypes.TagTeamVs):
            slot.team = SlotTeam.Red

        slot.status = SlotStatus.NotReady
        slot.player = self.player

        self.player.match = match

        self.enqueue_matchjoin_success(match)
        match.update()

        return True
    
    def leave_match(self):
        if self.player.restricted:
            return
        
        if not self.player.match:
            return
        
        slot = self.player.match.get_slot(self.player)
        assert slot is not None

        if slot.status == SlotStatus.Locked:
            status = SlotStatus.Locked
        else:
            status = SlotStatus.Open

        slot.reset(status)
        self.leave_channel(self.player.match.chat, kick=True)

        if all(slot.empty for slot in self.player.match.slots):
            # Match is empty
            bancho.services.matches.remove(self.player.match)

            for player in bancho.services.players.in_lobby:
                player.handler.enqueue_match_disband(self.player.match.id)
        else:
            if self.player is self.player.match.host:
                # Player was host, transfer to next player
                for slot in self.player.match.slots:
                    if slot.status.value & SlotStatus.HasPlayer.value:
                        self.player.match.host = slot.player
                        self.player.match.host.handler.enqueue_match_transferhost()

            self.player.match.update()

        self.player.match = None

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

        self.player.logger.debug(f'Changed status: {self.player.status}')

        # Enqueue to other clients
        bancho.services.players.enqueue_stats(self.player)

    def handle_send_message(self, stream: StreamIn):
        sender    = stream.string()
        message   = stream.string()
        target    = stream.string()
        sender_id = stream.s32()

        if target.startswith('#multiplayer'):
            if self.player.match:
                target = self.player.match.chat.name
            else:
                return

        if target.startswith('#spectator'):
            if self.player.spectating:
                target = f'#spec_{self.player.spectating.id}'
            
            elif self.player.spectators:
                target = f'#spec_{self.player.id}'

            else:
                return

        if not (channel := bancho.services.channels.by_name(target)):
            # Channel was not found
            return
        
        from bancho import commands
        
        # Check for commands
        if (command := commands.get_command(self.player, channel, message)):
            # A command was executed
            if command.hidden:
                # Command will only be shown to the player
                for line in command.response:
                    self.enqueue_message(bancho.services.bot_player, line, channel.display_name)
            else:
                channel.send_message(self.player, message)

                for line in command.response:
                    channel.send_message(bancho.services.bot_player, line)
            return

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

        # Limit message size
        if len(message) > 512:
            message = message[:512] + '... (truncated)'

        if player.status.action == ClientStatus.Afk and player.away_message:
            self.enqueue_message(player, player.away_message, target)

        # TODO: Commands

        self.player.logger.info(f'[PM -> {player.name}]: {message}')

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
        if self.player.restricted:
            return

        for player in bancho.services.players.in_lobby:
            player.handler.enqueue_lobby_join(self.player.id)

        for match in bancho.services.matches:
            if match is not None:
                self.enqueue_match(match)

        self.player.in_lobby = True

    def handle_part_lobby(self, stream: StreamIn):
        if self.player.restricted:
            return

        self.player.in_lobby = False

        for player in bancho.services.players.in_lobby:
            player.handler.enqueue_lobby_part(self.player.id)

    def handle_join_channel(self, stream: StreamIn):
        name = stream.string()

        if name.startswith('#spectator'):
            if self.player.spectating:
                name = f'#spec_{self.player.spectating.id}'
            elif self.player.spectators:
                name = f'#spec_{self.player.id}'
            else:
                self.enqueue_channel_revoked('#spectator')
                return
        
        elif name.startswith('#multiplayer'):
            if self.player.match:
                name = self.player.match.chat.name
            else:
                self.enqueue_channel_revoked('#multiplayer')
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

        self.player.logger.info(f'Added {target.name} as their friend')
        
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

        self.player.logger.info(f'Removed {target.name} as their friend')

        # Reload relationships
        self.player.reload_object()

        # Enqueue friends to client
        self.enqueue_friends()

    def handle_set_away_message(self, stream: StreamIn):
        _            = stream.string()
        away_message = stream.string()

        self.player.away_message = away_message

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
        
        if target == bancho.services.bot_player:
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

        if not self.player.spectating:
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

    def read_match(self, stream: StreamIn):
        
        from ..objects.multiplayer import Match

        match_id = stream.s16()

        in_progress = stream.bool()
        match_type = MatchType(stream.u8())
        mods = Mod.list(stream.u32())

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
        freemod            = stream.bool()

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

        if freemod:
            for i in range(8):
                m.slots[i].mods = Mod.list(stream.u32())

        return m
    
    def write_match(self, match, stream: StreamOut, send_password: bool = False):
        stream.u16(match.id)
        stream.bool(match.in_progress)
        stream.u8(match.type.value)
        stream.u32(Mod.pack(match.mods))
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
        stream.u8(int(match.freemod))

        if match.freemod:
            [stream.s32(Mod.pack(slot.mods)) for slot in match.slots]

        return stream

    def handle_create_match(self, stream: StreamIn):

        match = self.read_match(stream)

        if not self.player.in_lobby:
            self.enqueue_matchjoin_fail()
            return
        
        if self.player.restricted or self.player.silenced:
            self.enqueue_matchjoin_fail()
            return
        
        if not bancho.services.matches.append(match):
            self.enqueue_matchjoin_fail()
            return
        
        bancho.services.channels.append(
            c := Channel(
                name=f'#multi_{match.id}',
                topic=match.name,
                read_perms=1,
                write_perms=1,
                public=False
            )
        )
        match.chat = c

        self.player.logger.info(f'Created match: "{match.name}"')

        self.join_match(match, match.password)

    def handle_join_match(self, stream: StreamIn):
        match_id = stream.s32()
        password = stream.string()

        if not (match := bancho.services.matches[match_id]):
            self.enqueue_matchjoin_fail()
            self.enqueue_match_disband(match_id)
            return

        self.join_match(match, password)

    def handle_leave_match(self, stream: StreamIn):
        self.leave_match()

    def handle_match_change_slot(self, stream: StreamIn):
        if self.player.restricted:
            return

        if not self.player.match:
            return
        
        slot_id = stream.s32()

        if not 0 <= slot_id < 8:
            return
        
        if self.player.match.slots[slot_id].status != SlotStatus.Open:
            return
        
        slot = self.player.match.get_slot(self.player)
        assert slot is not None

        self.player.match.slots[slot_id].copy_from(slot)
        slot.reset()

        self.player.match.update()

    def handle_match_ready(self, stream: StreamIn):
        if self.player.restricted:
            return

        if not self.player.match:
            return
        
        slot = self.player.match.get_slot(self.player)
        assert slot is not None

        slot.status = SlotStatus.Ready
        self.player.match.update()

    def handle_match_not_ready(self, stream: StreamIn):
        if self.player.restricted:
            return

        if not self.player.match:
            return
        
        slot = self.player.match.get_slot(self.player)
        assert slot is not None

        slot.status = SlotStatus.NotReady
        self.player.match.update()

    def handle_match_no_beatmap(self, stream: StreamIn):
        if self.player.restricted:
            return

        if not self.player.match:
            return

        slot = self.player.match.get_slot(self.player)
        assert slot is not None

        slot.status = SlotStatus.NoMap
        self.player.match.update()

    def handle_match_has_beatmap(self, stream: StreamIn):
        self.handle_match_not_ready(stream)

    def handle_match_lock(self, stream: StreamIn):
        if self.player.restricted:
            return

        if not self.player.match:
            return

        if self.player is not self.player.match.host:
            return
        
        slot_id = stream.s32()
        
        if not 0 <= slot_id < 8:
            return
        
        slot = self.player.match.slots[slot_id]

        if slot.status == SlotStatus.Locked:
            slot.status = SlotStatus.Open
        else:
            if slot.player is self.player:
                # Players can't kick themselves
                return
            
            slot.status = SlotStatus.Locked

        self.player.match.update()

    def handle_match_change_settings(self, stream: StreamIn):
        if self.player.restricted:
            return

        if not self.player.match:
            return

        if self.player is not self.player.match.host:
            return

        self.player.match.change_settings(
            self.read_match(stream)
        )

    def handle_match_change_mods(self, stream: StreamIn):
        if self.player.restricted:
            return

        if not self.player.match:
            return
        
        mods = Mod.list(stream.u32())

        if self.player.match.freemod:
            # TODO: What is "FreeModAllowed"?

            if self.player is self.player.match.host:
                self.player.match.mods = [mod for mod in mods if mod in SPEED_MODS and mod != Mod.FreeModAllowed]

            slot = self.player.match.get_slot(self.player)
            assert slot is not None

            slot.mods = [mod for mod in mods if mod not in SPEED_MODS and mod != Mod.FreeModAllowed]

            self.player.logger.info(f'{self.player.name} changed their mods to: {"".join([mod.short for mod in mods])}')
        else:
            if self.player is not self.player.match.host:
                return
            
            self.player.match.mods = [mod for mod in mods if mod != Mod.FreeModAllowed]

            self.player.logger.info(f'Changed mods to: {"".join([mod.short for mod in mods])}')

        self.player.match.remove_invalid_mods()
        self.player.match.update()

    def handle_match_change_team(self, stream: StreamIn):
        if self.player.restricted:
            return

        if not self.player.match:
            return
        
        if not self.player.match.ffa:
            return
        
        slot = self.player.match.get_slot(self.player)
        assert slot is not None

        if slot.team == SlotTeam.Blue:
            slot.team = SlotTeam.Red
        else:
            slot.team = SlotTeam.Blue

        self.player.match.update()

    def handle_match_start(self, stream: StreamIn):
        if self.player.restricted:
            return

        if not self.player.match:
            return
        
        if self.player is not self.player.match.host:
            return
        
        self.player.match.start()

    def handle_match_score_update(self, stream: StreamIn):
        if self.player.restricted:
            return

        if not self.player.match:
            return
        
        if not self.player.match.in_progress:
            return
        
        slot, id = self.player.match.get_slot_with_id(self.player)
        assert slot is not None

        if not slot.is_playing:
            return
        
        score_frame = bytearray(stream.readall())
        score_frame[4] = id

        self.player.match.enqueue_score_update(bytes(score_frame))

    def handle_match_complete(self, stream: StreamIn):
        if self.player.restricted:
            return

        if not self.player.match:
            return
        
        if not self.player.match.in_progress:
            return
        
        slot = self.player.match.get_slot(self.player)
        assert slot is not None

        slot.status = SlotStatus.Complete

        if any([slot.is_playing for slot in self.player.match.slots]):
            return
        
        # Players that have been playing this round
        players = [
            slot.player for slot in self.player.match.slots
            if slot.status.value & SlotStatus.Complete.value
            and slot.has_player
        ]

        self.player.match.unready_players(SlotStatus.Complete)
        self.player.match.in_progress = False

        for player in players:
            player.handler.enqueue_match_complete()

        self.player.match.logger.info('Match finished')

        self.player.match.update()

    def handle_match_load_complete(self, stream: StreamIn):
        if self.player.restricted:
            return

        if not self.player.match:
            return
        
        if not self.player.match.in_progress:
            return
        
        slot = self.player.match.get_slot(self.player)
        assert slot is not None

        slot.loaded = True

        if all(
                [
                    slot.is_playing
                    for slot in self.player.match.slots
                    if slot.has_player and slot.player in self.player.match.players_withmap
                ]
            ):
            for player in self.player.match.players_withmap:
                player.handler.enqueue_match_all_players_loaded()

            self.player.match.update()

    def handle_match_skip(self, stream: StreamIn):
        if self.player.restricted:
            return

        if not self.player.match:
            return
        
        if not self.player.match.in_progress:
            return
        
        slot, id = self.player.match.get_slot_with_id(self.player)
        assert slot is not None

        slot.skipped = True
        self.player.match.enqueue_player_skipped(id)

        for slot in self.player.match.slots:
            if slot.status == SlotStatus.Playing and not slot.skipped:
                return
            
        self.player.match.enqueue_skip()

    def handle_match_failed(self, stream: StreamIn):
        if self.player.restricted:
            return

        if not self.player.match:
            return
        
        if not self.player.match.in_progress:
            return
        
        slot_id = self.player.match.get_slot_id(self.player)
        assert slot_id is not None

        self.player.match.enqueue_player_failed(slot_id)

    def handle_match_transfer_host(self, stream: StreamIn):
        if self.player.restricted:
            return

        if not self.player.match:
            return
        
        if self.player is not self.player.match.host:
            return
        
        slot_id = stream.s32()

        if not 0 <= slot_id < 8:
            return
        
        if not (target := self.player.match.slots[slot_id].player):
            # Tried to transfer host into empty slot
            return
        
        self.player.match.host = target
        self.player.match.host.handler.enqueue_match_transferhost()

        self.player.match.logger.info(f'Changed host to {target.name}')

        self.player.match.update()

    def handle_match_change_password(self, stream: StreamIn):
        if self.player.restricted:
            return

        if not (match := self.player.match):
            return
        
        if self.player is not self.player.match.host:
            return
        
        match.password = self.read_match(stream).password

        self.player.match.update()

    def handle_match_invite(self, stream: StreamIn):
        if self.player.restricted:
            return

        if not (match := self.player.match):
            return
        
        if not (target := bancho.services.players.by_id(stream.s32())):
            return
        
        bot = bancho.services.bot_player
        
        stream = StreamOut()
        stream.string(bot.name)
        stream.string(f'{self.player.name} invited you to a match: "{match.embed}"')
        stream.string(target.name)
        stream.s32(bot.id)

        target.sendPacket(
            ResponsePacket.INVITE,
            stream.get()
        )

    def handle_tournament_match_info(self, stream: StreamIn):
        if self.player.restricted:
            return
        
        # TODO: Check privileges and client
        
        match_id = stream.s32()

        if not 0 <= match_id < 64:
            return
        
        if not (match := bancho.services.matches[match_id]):
            return
        
        self.enqueue_match(match, update=True)

    def handle_error_report(self, stream: StreamIn):
        # TODO: Better error handling
        self.player.logger.warning(stream.string())
