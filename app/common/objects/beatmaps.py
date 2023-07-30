
from dataclasses import dataclass
from typing import List

@dataclass
class BeatmapInfo:
    index: int
    beatmap_id: int
    beatmapset_id: int
    thread_id: int
    ranked: int
    osu_rank: int
    fruits_rank: int
    taiko_rank: int
    mania_rank: int
    checksum: str

@dataclass
class BeatmapInfoReply:
    amount: int
    beatmaps: List[BeatmapInfo]

@dataclass
class BeatmapInfoRequest:
    filenames: List[str]
    beatmap_ids: List[int]
