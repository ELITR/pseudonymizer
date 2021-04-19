import csv
from typing import TextIO

import spacy


class Spacy():
    def __init__(self) -> None:
        # Prepare NER tagger with english model
        self._nlp = spacy.load("en_core_web_sm")

    def recognize(self, input: TextIO, writer: csv.DictWriter) -> None:
        lines = ''.join(input.readlines())

        document = self._nlp(lines)
        for ent in document.ents:
            writer.writerow({"start": ent.start_char, "end": ent.end_char, "text": ent.text, "type": ent.label_})
