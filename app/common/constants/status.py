
from enum import IntEnum

class SubmissionStatus(IntEnum):
    NotSubmitted   = -1
    Pending        = 0
    Unknown        = 1
    EditableCutoff = 2
    Approved       = 3
    Ranked         = 4

    @classmethod
    def from_database(cls, status: int):
        return {
            -2: SubmissionStatus.Pending,        # Graveyard
            -1: SubmissionStatus.EditableCutoff, # WIP
            0:  SubmissionStatus.Pending,        # Pending
            1:  SubmissionStatus.Ranked,         # Ranked
            2:  SubmissionStatus.Approved,       # Approved
            3:  SubmissionStatus.Ranked,         # Qualified
            4:  SubmissionStatus.Approved        # Loved
        }[status]
