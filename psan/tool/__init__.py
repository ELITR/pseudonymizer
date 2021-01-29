import os
from typing import Callable, Container, Optional

from psan.tool.annotater import find_evidence
from psan.tool.model import Candidate, Evidence, Rule
from psan.tool.ner import NameTag, RegexNer

default_ner = RegexNer(RegexNer.TWO_UPPERCASE_WORDS)


def recognize_file(input_filename: str, output_filename: str) -> int:
    if os.environ.get("NER_MODEL"):
        ner = NameTag(os.environ.get("NER_MODEL"))
    else:
        ner = default_ner

    return ner.recognize_file(input_filename, output_filename)


def auto_decide_file(filename: str,  open_candidates: Container[Candidate],
                     rule_finder: Callable[[Evidence], Optional[Rule]],
                     decision_updater: Callable[[Candidate, Rule], None]) -> None:
    # Find evidences in provided XML file
    evidences = find_evidence(filename, open_candidates)
    for evidence in evidences:
        # Find rule for each evidence
        rule = rule_finder(evidence)
        if rule:
            # Update decision
            decision_updater(evidence.candidate, rule)
