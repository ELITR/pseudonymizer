"""Named entity recognizer module."""

import re
from abc import ABC, abstractclassmethod
from typing import Pattern


class Ner(ABC):
    """Named entity recognizer abstract class."""

    @abstractclassmethod
    def recognize_file(self, input_filename: str, output_filename: str) -> None:
        pass


class RegexNer(Ner):

    TWO_UPPERCASE_WORDS = r"[A-Z][a-z]+\s[A-Z][a-z]+"

    def __init__(self, pattern: str) -> None:
        self._pattern = re.compile(f"({pattern})")

    def recognize_file(self, input_filename: str, output_filename: str) -> int:
        N = 0
        with open(input_filename, mode="r") as input, open(output_filename, mode="w") as output:
            for line in input.readlines():
                parsed, n = self._pattern.subn(r"<danger>\1</danger>", line)
                output.write(parsed)
                output.write('\n')
                N += n

        return N
