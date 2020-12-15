"""Named entity recognizer module."""

import re
import subprocess
from abc import ABC, abstractclassmethod
from typing import List

from ufal.nametag import Forms, NamedEntities, Ner, TokenRanges


class NerInterface(ABC):
    """Named entity recognizer abstract class."""

    @abstractclassmethod
    def recognize_file(self, input_filename: str, output_filename: str) -> int:
        pass


class RegexNer(NerInterface):
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


class BinaryNer(NerInterface):
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


class NameTag(NerInterface):
    """Named entity recognizer using NameTag2 from UFAL MFF UK"""

    def __init__(self, model_location) -> None:
        # Load model
        self._ner = Ner.load(model_location)
        if not self._ner:
            raise ValueError(
                f"Cannot load recognizer from file {model_location}")

        # Load tokenizer
        self._tokenizer = self._ner.newTokenizer()
        if not self._tokenizer:
            raise ValueError(
                "No tokenizer is defined for the supplied model!")

    @staticmethod
    def encode_entities(text: str):
        """Escapes XML entities to safe variants (`&` to `&amp;`)"""
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

    def recognize_file(self, input_filename: str, output_filename: str) -> int:
        forms = Forms()
        tokens = TokenRanges()
        entities = NamedEntities()

        N = 0
        with open(input_filename, mode="r") as input, open(output_filename, mode="w") as output:
            for line in input.readlines():
                # Tokenize line
                self._tokenizer.setText(line)

                t = 0
                while self._tokenizer.nextSentence(forms, tokens):
                    # Recognize named entities
                    self._ner.recognize(forms, entities)
                    sortedEntities = sorted(entities,
                                            key=lambda entity: (entity.start, -entity.length))
                    openEntities: List[int] = []

                    # Write entities to output
                    e = 0
                    for i in range(len(tokens)):
                        output.write(NameTag.encode_entities(
                            line[t:tokens[i].start]))

                        # Open entities starting at current token
                        while (e < len(sortedEntities) and sortedEntities[e].start == i):
                            output.write(
                                f"<ne type=\"{NameTag.encode_entities(sortedEntities[e].type)}\" id={N}>")
                            openEntities.append(
                                sortedEntities[e].start + sortedEntities[e].length - 1)
                            e = e + 1
                            N += 1

                        # The token itself
                        output.write(NameTag.encode_entities(
                            line[tokens[i].start: tokens[i].start + tokens[i].length]))

                        # Close entities ending after current token
                        while openEntities and openEntities[-1] == i:
                            output.write('</ne>')
                            openEntities.pop()
                        t = tokens[i].start + tokens[i].length
                # Write rest of the text
                output.write(NameTag.encode_entities(line[t:]))

        return N
