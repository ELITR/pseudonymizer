import xml.sax  # nosec - parse only internal XML
import xml.sax.handler  # nosec - parse only internal XML
from typing import Container, List, Tuple

from psan.tool.model import Candidate, Evidence


def find_evidence(filename: str, open_candidates: Container[Candidate]) -> List[Evidence]:
    """ Finds Evidence for open_candidates in provided file """
    parser = xml.sax.make_parser()  # nosec - parse only internal XML
    parser.setFeature(xml.sax.handler.feature_namespaces, 0)
    handler = EvidenceParser(open_candidates)
    parser.setContentHandler(handler)
    parser.parse(filename)

    return handler.evidences


class EvidenceParser(xml.sax.ContentHandler):
    """ Finds name entity type and tokens for each open candidate in provided XML """

    def __init__(self, open_candidates: Container[Candidate]) -> None:
        super().__init__()
        self._candidate_stack: List[Tuple[Candidate, str]] = []
        self._token_list: List[str] = []
        self._token_list_first_id = -1
        self._last_token_id = -1
        self._open_candidates = open_candidates
        self.evidences: List[Evidence] = []

    def startElement(self, tag, attrs):
        if tag == "ne":
            # Get params from XML
            start = int(attrs.get("start"))
            end = int(attrs.get("end"))
            ne_type = attrs.get("type")
            # Check if candidate is open
            candidate = Candidate(start, end)
            if candidate in self._open_candidates:
                # Add info to the stack
                if (len(self._candidate_stack) == 0):
                    self._token_list_first_id = start
                self._candidate_stack.append((candidate, ne_type))
        elif tag == "token":
            self._last_token_id = int(attrs.get("id"))

    def characters(self, content):
        # Save highlighted tokens
        if len(self._candidate_stack) > 0:
            text = content.strip()
            if len(text) > 0:
                self._token_list.append(text)

    def endElement(self, tag):
        if tag == "ne":
            last_candidate, last_ne_type = self._candidate_stack[-1]
            if last_candidate.end == self._last_token_id:
                # Cut tokens from list
                offset = self._token_list_first_id
                start = last_candidate.start - offset
                end = last_candidate.end - offset
                # Save evidence
                self.evidences.append(Evidence(last_candidate, last_ne_type, self._token_list[start: end + 1]))
                self._candidate_stack.pop()
                # Clear up tokens if there is nothing to track
                if len(self._candidate_stack) == 0:
                    self._token_list = []
                    self._token_list_first_id = -1
