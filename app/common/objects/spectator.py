
from dataclasses import dataclass
from typing import List, Optional

from ..constants import ButtonState, ReplayAction

@dataclass
class ScoreFrame:
    time: int
    id: int
    c300: int
    c100: int
    c50: int
    cGeki: int
    cKatu: int
    cMiss: int
    total_score: int
    max_combo: int
    current_combo: int
    perfect: bool
    hp: int
    tag_byte: int

@dataclass
class ReplayFrame:
    button_state: ButtonState
    taiko_byte: int
    mouse_x: float
    mouse_y: float
    time: int

@dataclass
class ReplayFrameBundle:
    extra: int
    action: ReplayAction
    replay_frames: List[ReplayFrame]
    frames: List[ReplayFrame]
    score_frame: Optional[ScoreFrame] = None
