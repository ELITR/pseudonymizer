from enum import Enum, IntFlag
from typing import List, NamedTuple


class AnnotationDecision(Enum):
    SECRET = "SECRET"  # nosec
    PUBLIC = "PUBLIC"
    NESTED = "NESTED"


class RuleType(Enum):
    WORD_TYPE = "WORD_TYPE"
    LEMMA = "LEMMA"
    NE_TYPE = "NE_TYPE"


class Confidence:
    CANDIDATE = 0


class Interval(NamedTuple):
    start: int
    end: int


class EvidenceType(IntFlag):
    NONE = 0
    NE_TYPE = 1
    LEMMA = 2
    WORD_TYPE = 3
    CONTEXT = 4


class Evidence(NamedTuple):
    type: EvidenceType
    interval: Interval
    value: List[str]


class Word(NamedTuple):
    token: str


class Rule(NamedTuple):
    id: int
