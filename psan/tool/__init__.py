from psan.tool.ner import RegexNer

default_ner = RegexNer(RegexNer.TWO_UPPERCASE_WORDS)


def recognize_file(input_filename: str, output_filename: str) -> int:
    return default_ner.recognize_file(input_filename, output_filename)
