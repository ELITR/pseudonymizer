import csv

import spacy


class Spacy():
    def __init__(self) -> None:
        # Prepare NER tagger with english model
        self._nlp = spacy.load("en_core_web_sm")

    def recognize(self, input, output):
        # Output
        writer = csv.writer(output)
        lines = ''.join(input.readlines())

        document = self._nlp(lines)
        for ent in document.ents:
            writer.writerow((ent.start_char, ent.end_char, ent.text, ent.label_))
