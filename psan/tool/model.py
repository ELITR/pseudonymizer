from typing import List, NamedTuple


class Candidate(NamedTuple):
    start: int
    end: int


class Evidence(NamedTuple):
    candidate: Candidate
    ne_type: str
    tokens: List[str]


class Rule(NamedTuple):
    id: int
