
from ..b20130815 import Reader as BaseReader

from app.common.objects import bReplayFrameBundle
from app.common.constants import ReplayAction

class Reader(BaseReader):
    def read_replayframe_bundle(self) -> bReplayFrameBundle:
        replay_frames = [self.read_replayframe() for f in range(self.stream.u16())]
        action = ReplayAction(self.stream.u8())
        extra = 0

        try:
            score_frame = self.read_scoreframe()
        except Exception:
            score_frame = None

        return bReplayFrameBundle(
            extra,
            action,
            replay_frames,
            score_frame
        )
