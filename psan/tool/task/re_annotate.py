import xml.sax  # nosec - parse only internal XML
import xml.sax.handler  # nosec - parse only internal XML
from typing import List

from psan.tool.controller import Controller
from psan.tool.model import Evidence, EvidenceType, Interval, Word
from psan.tool.parser import AnnotationParser, LookupEvent


def apply_rules(filename: str, ctl: Controller) -> None:
    # Find evidences in provided XML
    parser = xml.sax.make_parser()  # nosec - parse only internal XML
    parser.setFeature(xml.sax.handler.feature_namespaces, 0)
    handler = ReAnnotateParser(ctl)
    parser.setContentHandler(handler)
    parser.parse(filename)


class ReAnnotateParser(AnnotationParser):
    """ Finds name entity type and tokens for each open candidate in provided XML """

    def __init__(self, ctl: Controller):
        super().__init__()
        self._ctl = ctl

    def onWord(self, word: Word) -> None:
        super().onWord(word)

        # Future lookup length (for following words)
        type, lookup = self._ctl.rule_lookup(word)
        if type != EvidenceType.NONE:
            target_id = self._last_token_id + lookup
            event = LookupEvent(target_id, self._last_token_id, type)
            self.registerLookup(event)

    def onLookupEvent(self, event: LookupEvent, words: List[Word]) -> None:
        super().onLookupEvent(event, words)
        # Prepare evidence
        interval = Interval(event.source_token_id, event.target_token_id)
        if event.data == EvidenceType.WORD_TYPE:
            tokens = [word.token for word in words]
            evidence = Evidence(EvidenceType.WORD_TYPE, interval, tokens)
            # Find rule for current evidence
            rule = self._ctl.find_rule(evidence)
            # Pass updated rule
            if rule:
                self._ctl.annotate_with_rule(evidence.interval, rule)
