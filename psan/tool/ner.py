"""Named entity recognizer module."""

import functools
import re
import subprocess
from abc import ABC, abstractclassmethod
from typing import List, Match

from ufal.nametag import Forms, NamedEntities, Ner, TokenRanges


class NerInterface(ABC):
    """Named entity recognizer abstract class."""

    @abstractclassmethod
    def recognize_file(self, input_filename: str, output_filename: str,  next_id=0) -> int:
        """Finds named entities in the input file and save the results to the output file.
        Each entity has an ID that starts with next_id."""
        pass


class RegexNer(NerInterface):
    """Named entity recognizer using regular expressions."""

    TWO_UPPERCASE_WORDS = r"[A-Z][a-z]+\s[A-Z][a-z]+"

    class ReplaceStatus:
        def __init__(self, next_id: int) -> None:
            self.next_id = next_id

    def __init__(self, pattern: str) -> None:
        self._pattern = re.compile(f"({pattern})")

    @staticmethod
    def status_sub(match: Match, status: ReplaceStatus) -> str:
        new = f"<ne type=\"re\" id={status.next_id}>{match.group(1)}</ne>"
        status.next_id += 1
        return new

    def recognize_file(self, input_filename: str, output_filename: str, next_id=0) -> int:
        status = RegexNer.ReplaceStatus(next_id)
        status_sub_fn = functools.partial(RegexNer.status_sub, status=status)
        with open(input_filename, mode="r") as input, open(output_filename, mode="w") as output:
            for line in input:
                parsed = self._pattern.sub(status_sub_fn, line)
                output.write(parsed)
                output.write('\n')

        return status.next_id


class BinaryNer(NerInterface):
    """Named entity recognizer using external tool."""

    XML_TAG_PATTERN = re.compile(r"<ne", re.IGNORECASE)

    def __init__(self, binary_location: str, model_location: str) -> None:
        self._bin_loc = binary_location
        self._model_loc = model_location

    def recognize_file(self, input_filename: str, output_filename: str, next_id=0) -> int:
        # Call binary
        subprocess.call([self._bin_loc, self._model_loc,
                         f"{input_filename}:{output_filename}"])
        # Count found entries
        N = 0
        with open(output_filename, mode="r") as output:
            for line in output:
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

    def recognize_file(self, input_filename: str, output_filename: str, next_id=0) -> int:
        forms = Forms()
        tokens = TokenRanges()
        entities = NamedEntities()

        with open(input_filename, mode="r") as input, open(output_filename, mode="w") as output:
            for line in input:
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
                                f"<ne type=\"{NameTag.encode_entities(sortedEntities[e].type)}\" id=\"{next_id}\">")
                            openEntities.append(
                                sortedEntities[e].start + sortedEntities[e].length - 1)
                            e = e + 1
                            next_id += 1

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

        return next_id
