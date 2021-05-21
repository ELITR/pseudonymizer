import os

from psan.tool.ner import NameTag, RegexNer

default_ner = RegexNer(RegexNer.TWO_UPPERCASE_WORDS)


def recognize_file(input_filename: str, output_filename: str) -> int:
    """ Tokenize file and recognize name entities. Return number of tokens in file. """
    if os.environ.get("NER_MODEL"):
        ner = NameTag(os.environ.get("NER_MODEL"))
    else:
        ner = default_ner

    return ner.recognize_file(input_filename, output_filename)
