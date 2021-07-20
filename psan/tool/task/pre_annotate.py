import xml.sax  # nosec - parse only internal XML
import xml.sax.handler  # nosec - parse only internal XML
from typing import Dict, List

from psan.tool.controller import Controller
from psan.tool.model import AnnotationDecision, Interval, Rule, Word
from psan.tool.parser import AnnotationParser, LookupEvent


def detect_recognized_name_entries(recognized_file: str, controller: Controller) -> None:
    # Parse pre-annotated XML
    parser = xml.sax.make_parser()  # nosec - parse only internal XML
    parser.setFeature(xml.sax.handler.feature_namespaces, 0)
    handler = PreAnnotationParser(controller)
    parser.setContentHandler(handler)
    parser.parse(recognized_file)


class PreAnnotationParser(AnnotationParser):
    """Make rules from named entities in provided XML file"""

    def __init__(self, controller: Controller) -> None:
        super().__init__()
        self._ctl = controller
        self._ne_types: Dict[str, Rule] = dict()

    def onNameEntity(self, start: int, end: int, ne_type: str, depth) -> None:
        # Register NE type in db
        if ne_type not in self._ne_types:
            self._ne_types[ne_type] = self._ctl.add_ne_type(ne_type)

        # Token level decision
        nested = depth > 1
        decision = AnnotationDecision.NESTED if nested else None

        # Add annotation to db
        self._ctl.annotate_from_rule(Interval(start, end), self._ne_types[ne_type], decision)

    def onLookupEvent(self, event: LookupEvent, words: List[Word]) -> None:
        pass
