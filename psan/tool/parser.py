import xml
from heapq import heappop, heappush
from typing import Any, List, NamedTuple

from psan.tool.model import Word


class LookupEvent(NamedTuple):
    target_token_id: int
    source_token_id: int
    data: Any


class AnnotationParser(xml.sax.ContentHandler):
    """ Provides event driven API for psan's XML formated texts"""

    def __init__(self) -> None:
        super().__init__()
        # Word types and tokens
        self._word_list: List[Word] = []
        self._word_list_first_token_id = -1
        self._lookup_events: List[LookupEvent] = []
        # Current state
        self._last_token_id = -1
        self._last_token: str
        self._ne_depth = 0

    def startElement(self, tag, attrs):
        if tag == "ne":
            self._ne_depth += 1
            # Get params from XML
            start = int(attrs.get("start"))
            end = int(attrs.get("end"))
            ne_type = attrs.get("type")
            # Forward event
            self.onNameEntity(start, end, ne_type, self._ne_depth)
        elif tag == "token":
            self._last_token_id = int(attrs.get("id"))

    def characters(self, content):
        # Save token context
        self._last_token = content.strip()

    def endElement(self, tag):
        if tag == "token":
            # Save last word info
            last_word = Word(self._last_token)
            # Forward event
            self.onWord(last_word)
            # Current lookup event
            if len(self._lookup_events) > 0:
                if len(self._word_list) == 0:
                    self._word_list_first_token_id = self._last_token_id
                self._word_list.append(last_word)
                self._handleLookups(self._last_token_id)
        elif tag == "ne":
            self._ne_depth -= 1

    def registerLookup(self, event: LookupEvent) -> None:
        heappush(self._lookup_events, event)

    def _handleLookups(self, current_id: int) -> None:
        while len(self._lookup_events) > 0 and self._lookup_events[0].target_token_id == current_id:
            event = heappop(self._lookup_events)
            words = self._word_list[event.sequence.start - self._word_list_first_token_id:
                                    event.sequence.end - self._word_list_first_token_id + 1]
            # Forward event
            self.onLookupEvent(event, words)
            # Tokens cleanup
            if len(self._lookup_events) == 0:
                self._word_list_first_token_id = None
                self._word_list = []

    def onLookupEvent(self, event: LookupEvent, words: List[Word]) -> None:
        pass

    def onNameEntity(self, start: int, end: int, ne_type: str, depth: int) -> None:
        pass

    def onWord(self, word: Word) -> None:
        pass
