
from app.common.objects import bReplayFrameBundle

from ..b20130606 import Writer as BaseWriter

class Writer(BaseWriter):
    def write_replayframe_bundle(self, bundle: bReplayFrameBundle):
        self.stream.u16(len(bundle.frames))
        [self.write_replayframe(frame) for frame in bundle.frames]
        self.stream.u8(bundle.action.value)

        if bundle.score_frame:
            self.write_scoreframe(bundle.score_frame)
