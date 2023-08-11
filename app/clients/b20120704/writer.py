
from ..b20120725 import Writer as BaseWriter

from app.common.objects import bUserStats

class Writer(BaseWriter):
    def write_stats(self, stats: bUserStats):
        self.stream.s32(stats.user_id)
        self.write_status(stats.status)
        self.stream.u64(stats.rscore)
        self.stream.float(stats.accuracy)
        self.stream.s32(stats.playcount)
        self.stream.u64(stats.tscore)
        self.stream.s32(stats.rank)
