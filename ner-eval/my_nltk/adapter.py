import csv
from typing import TextIO

import nltk
from nltk.tag.stanford import StanfordNERTagger


class StanfordNer():
    def __init__(self) -> None:
        jar = './my_nltk/stanford-ner.jar'
        model = './my_nltk/english.all.3class.distsim.crf.ser.gz'

        # Prepare NER tagger with english model
        self._ner = StanfordNERTagger(model, jar, encoding='utf8')

    def recognize_file(self, input_filename: str, output_filename: str, token_id=0) -> None:
        with open(input_filename, mode="r") as input, open(output_filename, mode="w") as output:
            for line in input:
                # Tokenize: Split sentence into words
                words = nltk.word_tokenize(line)

                print(ner_tagger.tag(words))

    def recognize(self, input: TextIO, writer: csv.DictWriter) -> None:
        lines = ''.join(input.readlines())
        tokens = [nltk.word_tokenize(sentence) for sentence in nltk.sent_tokenize(lines)]

        name_entities = self._ner.tag_sents(tokens)

        text_possition = 0
        for sentence in name_entities:
            current_ne_type = None
            current_len = 0
            for token, ne_type in sentence:
                text_possition = lines.find(token, text_possition)
                if ne_type != 'O':
                    if current_ne_type == ne_type and lines[end:text_possition].isspace():
                        end = text_possition + len(token)
                        current_len += 1
                    else:
                        if current_len > 0:
                            # Write current text
                            writer.writerow({"start": start, "end": end, "text": lines[start:end],
                                             "type": current_ne_type, "token_len": current_len})
                        # Update stats
                        current_ne_type = ne_type
                        current_len = 1
                        start = text_possition
                        end = start + len(token)
                else:
                    if current_len > 0:
                        # Write current text
                        writer.writerow({"start": start, "end": end,
                                         "text": lines[start:end], "type": current_ne_type, "token_len": current_len})
                    # Update stats
                    current_ne_type = None
                    current_len = 0
                text_possition += len(token)
