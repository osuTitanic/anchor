
from dataclasses import dataclass
from typing import List

from app.common.constants import Grade

@dataclass
class BeatmapInfo:
    index: int
    beatmap_id: int
    beatmapset_id: int
    thread_id: int
    ranked: int
    osu_rank: Grade
    fruits_rank: Grade
    taiko_rank: Grade
    mania_rank: Grade
    checksum: str

@dataclass
class BeatmapInfoReply:
    beatmaps: List[BeatmapInfo]

@dataclass
class BeatmapInfoRequest:
    filenames: List[str]
    beatmap_ids: List[int]
