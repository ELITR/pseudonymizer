import csv
import sys
from contextlib import ExitStack
from time import sleep
from typing import Dict, Optional


class LazyReader():
    def __init__(self, reader: csv.DictReader) -> None:
        self._row = None
        self._reader = reader

    def next(self) -> None:
        self._row = None

    def __bool__(self):
        if self._row:
            return True
        else:
            return bool(self.value)

    @property
    def value(self) -> Optional[Dict]:
        if not self._row:
            try:
                self._row = next(self._reader)
            except StopIteration:
                return None
        return self._row


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(f"Usage {sys.argv[0]} output_file features_file ner_files...", file=sys.stderr)
        exit(1)
    _, output_file, features_file, *ner_files = sys.argv
    ner_names = [ner.split("/")[-1][:-4] for ner in ner_files]

    with open(features_file, "r") as feat_input, open(output_file, "w") as output, ExitStack() as stack:
        # Open CSV readers
        feats = csv.DictReader(feat_input)
        its = [LazyReader(csv.DictReader(stack.enter_context(open(file_name)))) for file_name in ner_files]
        # Open CSV writers
        writer = csv.DictWriter(output, ("start", "end", "text", *ner_names))
        writer.writeheader()

        for feat in feats:
            f_start = int(feat["start"])
            f_end = int(feat["end"])

            results = {"start": f_start, "end": f_end, "text": feat["text"]}

            for i, it in enumerate(its):

                while it and int(it.value["end"]) < f_start:
                    it.next()

                if it:
                    i_start = int(it.value["start"])
                    i_end = int(it.value["end"])
                    if i_start <= f_end and f_start <= i_end:
                        results[ner_names[i]] = it.value["text"]

            writer.writerow(results)
