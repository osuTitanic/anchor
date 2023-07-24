
from typing import List, Tuple

from bancho.common.objects import DBBeatmap
from bancho.streams import StreamOut
from bancho.constants import (
    ResponsePacket,
    Ranked,
    Grade
)

from .b20121119 import b20121119

import bancho

class b20121030(b20121119):
    def enqueue_beatmaps(self, beatmaps: List[Tuple[int, DBBeatmap]]):
        stream = StreamOut()
        stream.s32(len(beatmaps))

        for index, beatmap in beatmaps:
            stream.s16(index)
            stream.s32(beatmap.id)
            stream.s32(beatmap.set_id)
            stream.s32(beatmap.set_id) # TODO: Thread ID
            stream.s8(Ranked.from_status(beatmap.status).value)

            for mode in range(3):
                personal_best = bancho.services.database.personal_best(
                    beatmap.id,
                    self.player.id,
                    mode
                )

                if not personal_best:
                    stream.s8(Grade.N.value)
                    continue

                stream.s8(Grade[personal_best.grade].value)

            stream.string(beatmap.md5)

        self.player.sendPacket(
            ResponsePacket.BEATMAP_INFO_REPLY,
            stream.get()
        )

