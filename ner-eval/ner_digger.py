import sys

import my_nametag
from my_nltk.adapter import StanfordNer
from my_spacy.adapter import Spacy

if __name__ == "__main__":
    # Check input args
    if len(sys.argv) != 2:
        print(f"Usage {sys.argv[0]} ner_name", file=sys.stderr)
        print("input_file;output_file pairs on stdin", file=sys.stderr)
        exit(1)
    ner_name = sys.argv[1]

    if ner_name == "nametag":
        ner = my_nametag.get_ner()
    elif ner_name == "nltk":
        ner = StanfordNer()
    elif ner_name == "spacy":
        ner = Spacy()
    else:
        print("Unknown NER", file=sys.stderr)
        exit(1)

    for line in sys.stdin:
        input_file, output_file = line.strip().split(";")
        with open(input_file, "r") as input, open(output_file, "w") as output:
            ner.recognize(input, output)
