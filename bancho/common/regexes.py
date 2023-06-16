
import re

OSU_VERSION = re.compile(
    r"^b(?P<date>\d{1,8})"
    r"(?:(?P<name>[\w]*))?"
    r"(\.?)"
    r"(?:(?P<revision>\d))?"
    r"(?P<stream>dev|tourney|test)?$",
)
