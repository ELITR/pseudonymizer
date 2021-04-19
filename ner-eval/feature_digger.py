import csv
import sys
import xml.sax  # nosec - parse only internal XML
from collections import namedtuple
from distutils import text_file
from typing import Optional

Feature = namedtuple("Feature", ("start", "label"))


class FeatureParser(xml.sax.ContentHandler):
    """ Finds name entity type and tokens for each open candidate in provided XML """

    def __init__(self, feature_callback, txt_callback) -> None:
        super().__init__()
        self._feature_callback = feature_callback
        self._txt_callback = txt_callback
        self._possition = 0
        self._current: Optional[Feature] = None
        self._text = None

    def startElement(self, tag, attrs):
        if tag.lower() == "ne":
            # Parse arguments
            status = attrs.get("status")
            label = attrs.get("anonymizedlabel")
            # Check status
            if status.startswith("confirmed"):
                self._current = Feature(self._possition, label)
                self._text = ""

    def characters(self, content):
        self._possition += len(content)
        self._txt_callback(content)
        if self._current:
            self._text += content

    def endElement(self, tag):
        if self._current and tag.lower() == "ne":
            if self._possition > self._current.start:
                self._feature_callback(self._current.start, self._possition, self._text, self._current.label)
                self._current = None
                self._text = None


class DiscardErrorHandler:
    def __init__(self, parser):
        self.parser = parser

    def fatalError(self, msg):
        print(msg, file=sys.stderr)


if __name__ == "__main__":
    # Check arguments
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} input_file features_file txt_file", file=sys.stderr)
        exit(1)
    input_file = sys.argv[1]
    features_file = sys.argv[2]
    text_file = sys.argv[3]

    # Open input file
    with open(features_file, "w") as features_output, open(text_file, "w") as text_output:
        # Output format
        csv_writer = csv.DictWriter(features_output,  ("start", "end", "text", "label"))
        csv_writer.writeheader()

        def feature_callback(start, end, text, label):
            return csv_writer.writerow({"start": start, "end": end, "text": text, "label": label if label else ""})

        def txt_callback(text):
            return text_output.write(text)

        parser = xml.sax.make_parser()  # nosec - parse only internal XML
        parser.setFeature(xml.sax.handler.feature_namespaces, False)
        parser.setFeature(xml.sax.handler.feature_validation, False)
        handler = FeatureParser(feature_callback, txt_callback)
        parser.setContentHandler(handler)
        parser.setErrorHandler(DiscardErrorHandler(parser))
        parser.parse(input_file)
