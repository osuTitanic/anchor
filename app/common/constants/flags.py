
from enum import IntFlag

class BadFlags(IntFlag):
	Clean                       = 0
	SpeedHackDetected           = 2
	IncorrectModValue           = 4
	MultipleOsuClients          = 8
	ChecksumFailure             = 16
	FlashlightChecksumIncorrect = 32
	OsuExecutableChecksum       = 64
	MissingProcessesInList      = 128
	FlashLightImageHack         = 256
	SpinnerHack                 = 512
	TransparentWindow           = 1024
	FastPress                   = 2048
