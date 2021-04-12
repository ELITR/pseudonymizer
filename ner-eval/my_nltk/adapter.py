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

    def recognize(self, input, output):
        # Output
        writer = csv.writer(output)
        lines = ''.join(input.readlines())
        tokens = [nltk.word_tokenize(sentence) for sentence in nltk.sent_tokenize(lines)]

        name_entities = self._ner.tag_sents(tokens)

        text_possition = 0
        sentence_id = 0
        for sentence in name_entities:
            for token, ne_type in sentence:
                text_possition = lines.find(token, text_possition)
                if ne_type != 'O':
                    start = text_possition - sentence_id
                    end = start + len(token)
                    writer.writerow((start, end, token, ne_type, 1))
                text_possition += len(token)
            sentence_id += 1
