import csv
from typing import List, TextIO

from ufal.nametag import Forms, NamedEntities, Ner, TokenRanges


class NameTag():
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

    def recognize_file(self, input_filename: str, output_filename: str, token_id=0) -> None:
        forms = Forms()
        tokens = TokenRanges()
        entities = NamedEntities()

        with open(input_filename, mode="r") as input, open(output_filename, mode="w") as output:
            # Write document header
            output.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
            output.write("<submission>\n")
            for line in input:
                # Tokenize line
                self._tokenizer.setText(line)

                text_position = 0
                while self._tokenizer.nextSentence(forms, tokens):
                    # Recognize named entities
                    self._ner.recognize(forms, entities)
                    sortedEntities = sorted(entities,
                                            key=lambda entity: (entity.start, -entity.length))
                    openEntities: List[int] = []

                    # Write entities to output
                    ne_index = 0
                    for token_index in range(len(tokens)):
                        output.write(NameTag.encode_entities(
                            line[text_position:tokens[token_index].start]))
                        if (token_index == 0):
                            output.write(
                                f"<sentence start=\"{token_id}\" end=\"{token_id+len(tokens)}\">")

                        # Open entities starting at current token
                        while (ne_index < len(sortedEntities) and sortedEntities[ne_index].start == token_index):
                            # Count name entry tokens index range
                            start_token_index = sortedEntities[ne_index].start
                            end_token_index = sortedEntities[ne_index].start + \
                                sortedEntities[ne_index].length - 1
                            # Count name entry tokens id range
                            start_token_id = token_id - token_index + start_token_index
                            end_token_id = token_id - token_index + end_token_index
                            # Write XML entry
                            output.write(
                                f"<ne type=\"{NameTag.encode_entities(sortedEntities[ne_index].type)}\""
                                f" start=\"{start_token_id}\" end=\"{end_token_id}\">")
                            openEntities.append(end_token_index)
                            ne_index = ne_index + 1

                        # The token itself
                        output.write(f"<token id=\"{token_id}\">")
                        token_id += 1
                        output.write(NameTag.encode_entities(
                            line[tokens[token_index].start: tokens[token_index].start + tokens[token_index].length]))
                        output.write("</token>")

                        # Close entities ending after current token
                        while openEntities and openEntities[-1] == token_index:
                            output.write("</ne>")
                            openEntities.pop()
                        if (token_index + 1 == len(tokens)):
                            output.write("</sentence>")
                        text_position = tokens[token_index].start + \
                            tokens[token_index].length
                # Write rest of the text
                output.write(NameTag.encode_entities(line[text_position:]))
            output.write("\n</submission>")

    def recognize(self, input: TextIO, writer: csv.DictWriter) -> None:
        # NameTag object
        forms = Forms()
        tokens = TokenRanges()
        entities = NamedEntities()

        line_start_offset = 0
        for line in input:
            # Tokenize line
            self._tokenizer.setText(line)

            while self._tokenizer.nextSentence(forms, tokens):
                # Recognize named entities
                self._ner.recognize(forms, entities)
                sorted_name_entries = sorted(entities,
                                             key=lambda entity: (entity.start, -entity.length))

                # Write entities to output
                for name_entry in sorted_name_entries:
                    # Count name entry tokens index range
                    start_token_index = name_entry.start
                    end_token_index = name_entry.start + name_entry.length - 1
                    # Count name entry tokens id range
                    text_start = line_start_offset + tokens[start_token_index].start
                    text_end = line_start_offset + tokens[end_token_index].start + tokens[end_token_index].length
                    text = line[tokens[start_token_index].start: tokens[end_token_index].start + tokens[end_token_index].length]
                    # Write output
                    writer.writerow({"start": text_start, "end": text_end, "text": text,
                                     "type": name_entry.type, "token_len": name_entry.length})
            # Move offset
            line_start_offset += len(line)
