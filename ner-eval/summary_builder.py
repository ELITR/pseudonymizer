import csv
import sys
from contextlib import ExitStack
from dataclasses import dataclass
from typing import Dict, Optional


class LazyReader():
    def __init__(self, reader: csv.DictReader) -> None:
        self._row = None
        self._reader = reader
        self.line_num = 0

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
                self.line_num += 1
            except StopIteration:
                return None
        return self._row


@dataclass
class MatchStat:
    exact = 0
    inside = 0
    partial = 0
    lines = 0

    def __str__(self) -> str:
        return f"{self.exact},{self.inside},{self.partial},{self.lines}"


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
        writer = csv.DictWriter(output, ("start", "end", "text", *ner_names, *(f"{ner}-raw" for ner in ner_names)))
        writer.writeheader()
        # Stats
        num_features = 0
        summary = dict()
        for name in ner_names:
            summary[name] = MatchStat()

        for feat in feats:
            num_features += 1
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
                        results[f"{ner_names[i]}-raw"] = it.value["text"]
                        if i_start == f_start and i_end == f_end:
                            results[ner_names[i]] = "EXACT"
                            summary[ner_names[i]].exact += 1
                        elif i_start <= f_start and f_end <= i_end:
                            results[ner_names[i]] = "INSIDE"
                            summary[ner_names[i]].inside += 1
                        else:
                            results[ner_names[i]] = "PARTIAL"
                            summary[ner_names[i]].partial += 1

            writer.writerow(results)

        # Update global stats
        summary["_features"] = num_features
        for i, it in enumerate(its):
            summary[ner_names[i]].lines = it.line_num
        # Print stats
        data = sorted(summary.items())
        values = (str(value) for key, value in data)
        print(",".join(values))
