import csv

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
