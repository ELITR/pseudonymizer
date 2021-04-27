import csv
import sys

import ahocorasick

import my_nametag
from my_nltk.adapter import StanfordNer
from my_spacy.adapter import Spacy

NER_HEADER = ("start", "end", "text", "type", "token_len")

if __name__ == "__main__":
    # Check input args
    if len(sys.argv) != 2:
        print(f"Usage {sys.argv[0]} ner_name", file=sys.stderr)
        print("input_file;output_file;output_plus_file  on stdin", file=sys.stderr)
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
        input_file, ner_file, ner_plus_file = line.strip().split(";")
        with open(input_file, "r") as input, open(ner_file, "w") as output:
            csv_writer = csv.DictWriter(output, NER_HEADER)
            csv_writer.writeheader()
            ner.recognize(input, csv_writer)

        # Improved (plus) version
        ac_automata = ahocorasick.Automaton()
        with open(ner_file, "r") as ner_data:
            ner_reader = csv.DictReader(ner_data)
            for i, row in enumerate(ner_reader):
                text = row["text"]
                ac_automata.add_word(text, (i, text))
        ac_automata.make_automaton()

        with open(input_file, "r") as input, open(ner_file, "r") as ner_data, open(ner_plus_file, "w") as ner_plus_data:
            ner_reader = csv.DictReader(ner_data)
            writer = csv.DictWriter(ner_plus_data, NER_HEADER)
            writer.writeheader()
            try:
                ner_row = next(ner_reader)
                ner_start = int(ner_row["start"])
                ner_end = int(ner_row["end"])
            except StopIteration:
                ner_row = None
                ner_start = None
                ner_end = None

            lines = ''.join(input.readlines())
            for ac_end, (_, ac_text) in ac_automata.iter(lines):
                # ac_automata position
                ac_start = ac_end - len(ac_text) + 1
                ac_end += 1

                # Move to next NER row
                while ner_row and ner_end <= ac_start:
                    # Write row from NER
                    writer.writerow(ner_row)
                    try:
                        ner_row = next(ner_reader)
                        ner_start = int(ner_row["start"])
                        ner_end = int(ner_row["end"])
                    except StopIteration:
                        ner_row = None
                        ner_start = None
                        ner_end = None

                # Write found text
                if ner_row is None or ac_end < ner_start:
                    writer.writerow({"start": ac_start, "end": ac_end,
                                     "text": ac_text, "type": "PLUS"})

            # Write remaining
            while ner_row:
                try:
                    writer.writerow(ner_row)
                    ner_row = next(ner_reader)
                except StopIteration:
                    ner_row = None
