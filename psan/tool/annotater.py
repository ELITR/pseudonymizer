import functools
import xml.sax  # nosec - parse only internal XML
import xml.sax.handler  # nosec - parse only internal XML
from heapq import heappop, heappush
from typing import Callable, List, NamedTuple, Optional, Tuple

from psan.tool.model import Candidate, Evidence, ReasonType, Rule, Word


def find_evidence(filename: str, evidence_callback: Callable[[Evidence], None],
                  word_lookup: Callable[[Word], Tuple[ReasonType, int]]) -> None:
    """ Finds Evidence in provided file """
    parser = xml.sax.make_parser()  # nosec - parse only internal XML
    parser.setFeature(xml.sax.handler.feature_namespaces, 0)
    handler = EvidenceParser(evidence_callback, word_lookup)
    parser.setContentHandler(handler)
    parser.parse(filename)


def auto_decide_file(filename: str, decision_reason_finder: Callable[[Candidate], ReasonType],
                     rule_finder: Callable[[Evidence], Optional[Rule]],
                     word_lookup: Callable[[Word], Tuple[ReasonType, int]],
                     decision_updater: Callable[[Candidate, Rule], None]) -> None:
    # Prepare callbacks
    evidence_callback = functools.partial(_evidence_handler, decision_reason_finder=decision_reason_finder,
                                          rule_finder=rule_finder, decision_updater=decision_updater)
    # Find evidences in provided XML
    find_evidence(filename, evidence_callback, word_lookup)


def _evidence_handler(evidence: Evidence,
                      decision_reason_finder: Callable[[Candidate], ReasonType],
                      rule_finder: Callable[[Evidence], Optional[Rule]],
                      decision_updater: Callable[[Candidate, Rule], None]) -> None:
    reason = decision_reason_finder(evidence.candidate)
    # Find better rule for actual candidate
    rule = None
    if evidence.type == ReasonType.NE_TYPE and reason < ReasonType.NE_TYPE:
        rule = rule_finder(evidence)
    elif evidence.type == ReasonType.WORD_TYPE and reason < ReasonType.WORD_TYPE:
        rule = rule_finder(evidence)
    # Pass updated rule
    if rule:
        decision_updater(evidence.candidate, rule)


class EvidenceParser(xml.sax.ContentHandler):
    """ Finds name entity type and tokens for each open candidate in provided XML """

    def __init__(self, evidence_callback: Callable[[Evidence], None],
                 word_lookup: Callable[[Word], Tuple[ReasonType, int]]) -> None:
        super().__init__()
        self._evidence_callback = evidence_callback
        # Word types and tokens
        self._lookup = word_lookup
        self._word_list: List[Word] = []
        self._lookup_events: List[LookupEvent] = []
        # Current state
        self._last_token_id = -1
        self._last_token: str

    def startElement(self, tag, attrs):
        if tag == "ne":
            # Get params from XML
            start = int(attrs.get("start"))
            end = int(attrs.get("end"))
            ne_type = attrs.get("type")
            # Forward name entry type evidence
            candidate = Candidate(start, end)
            self._evidence_callback(Evidence(ReasonType.NE_TYPE, candidate, [ne_type]))
        elif tag == "token":
            self._last_token_id = int(attrs.get("id"))

    def characters(self, content):
        # Save highlighted tokens
        self._last_token = content.strip()

    def endElement(self, tag):
        if tag == "token":
            # Save last word info
            last_word = Word(self._last_token)
            self._word_list.append(last_word)
            # Lookup length (for following words)
            type, lookup = self._lookup(last_word)
            if type != ReasonType.NONE:
                target_id = self._last_token_id + lookup
                self._registerLookup(self._last_token_id, target_id, type)
            self._handleLookups(self._last_token_id)

    def _registerLookup(self, current_id: int, target_id: int, type: ReasonType) -> None:
        heappush(self._lookup_events, LookupEvent(target_id, current_id, type))

    def _handleLookups(self, current_id: int):
        if len(self._lookup_events) > 0 and self._lookup_events[0].target_token_id == current_id:
            event = heappop(self._lookup_events)
            # Prepare evidence
            candidate = Candidate(event.source_token_id, event.target_token_id)
            if event.type == ReasonType.WORD_TYPE:
                types = [word.token for word in self._word_list[candidate.start:candidate.end + 1]]
                evidence = Evidence(ReasonType.WORD_TYPE, candidate, types)
                self._evidence_callback(evidence)


class LookupEvent(NamedTuple):
    target_token_id: int
    source_token_id: int
    type: ReasonType
