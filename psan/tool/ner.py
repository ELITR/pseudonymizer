"""Named entity recognizer module."""

import re
import subprocess
from abc import ABC, abstractclassmethod


class Ner(ABC):
    """Named entity recognizer abstract class."""

    @abstractclassmethod
    def recognize_file(self, input_filename: str, output_filename: str) -> int:
        pass


class RegexNer(Ner):
    """Named entity recognizer using regular expressions."""

    TWO_UPPERCASE_WORDS = r"[A-Z][a-z]+\s[A-Z][a-z]+"

    def __init__(self, pattern: str) -> None:
        self._pattern = re.compile(f"({pattern})")

    def recognize_file(self, input_filename: str, output_filename: str) -> int:
        N = 0
        with open(input_filename, mode="r") as input, open(output_filename, mode="w") as output:
            for line in input.readlines():
                parsed, n = self._pattern.subn(
                    r"<ne type=\"re\">\1</ne>", line)
                output.write(parsed)
                output.write('\n')
                N += n

        return N


class BinaryNer(Ner):
    """Named entity recognizer using external tool."""

    XML_TAG_PATTERN = re.compile(r"<ne", re.IGNORECASE)

    def __init__(self, binary_location: str, model_location: str) -> None:
        self._bin_loc = binary_location
        self._model_loc = model_location

    def recognize_file(self, input_filename: str, output_filename: str) -> int:
        # Call binary
        subprocess.call([self._bin_loc, self._model_loc,
                         f"{input_filename}:{output_filename}"])
        # Count found entries
        N = 0
        with open(output_filename, mode="r") as output:
            for line in output.readlines():
                N += len(BinaryNer.XML_TAG_PATTERN.findall(line))

        return N
