import os

from psan.tool.ner import BinaryNer, RegexNer

default_ner = RegexNer(RegexNer.TWO_UPPERCASE_WORDS)


def recognize_file(input_filename: str, output_filename: str) -> int:
    if os.environ.get("NER_BIN"):
        ner = BinaryNer(os.environ.get("NER_BIN"), os.environ.get("NER_MODEL"))
    else:
        ner = default_ner

    return ner.recognize_file(input_filename, output_filename)
