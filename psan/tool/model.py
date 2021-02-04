from enum import IntFlag
from typing import List, NamedTuple


class Candidate(NamedTuple):
    start: int
    end: int


class ReasonType(IntFlag):
    NONE = 0
    NE_TYPE = 1
    LEMMA = 2
    WORD_TYPE = 3
    CONTEXT = 4


class Evidence(NamedTuple):
    type: ReasonType
    candidate: Candidate
    value: List[str]


class Word(NamedTuple):
    token: str


class Rule(NamedTuple):
    id: int
