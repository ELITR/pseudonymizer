import csv
import sys
import xml.sax  # nosec - parse only internal XML
from collections import namedtuple
from typing import Optional

from py import std

Feature = namedtuple("Feature", ("start", "label"))


class FeatureParser(xml.sax.ContentHandler):
    """ Finds name entity type and tokens for each open candidate in provided XML """

    def __init__(self, feature_callbacks) -> None:
        super().__init__()
        self._feature_callback = feature_callbacks
        self._possition = 0
        self._current: Optional[Feature] = None

    def startElement(self, tag, attrs):
        if tag == "ne":
            # Parse arguments
            status = attrs.get("status")
            label = attrs.get("anonymizedlabel")
            # Check status
            if status.startswith("confirmed"):
                self._current = Feature(self._possition, label)

    def characters(self, content):
        self._possition += len(content)

    def endElement(self, tag):
        if tag == "ne" and self._current:
            if self._possition > self._current.start:
                self._feature_callback(self._current.start, self._possition, self._current.label)


class DiscardErrorHandler:
    def __init__(self, parser):
        self.parser = parser

    def fatalError(self, msg):
        print(msg, file=sys.stderr)


if __name__ == "__main__":
    # Check arguments
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} input_file output_file", file=sys.stderr)
        exit(1)
    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # Open input file
    with open(output_file, "w") as output:
        # Output format
        csv_writer = csv.writer(output)

        def feature_callback(start, end, label):
            return csv_writer.writerow((start, end, label if label else ""))

        parser = xml.sax.make_parser()  # nosec - parse only internal XML
        parser.setFeature(xml.sax.handler.feature_namespaces, False)
        parser.setFeature(xml.sax.handler.feature_validation, False)
        parser.setFeature(xml.sax.handler.feature_external_ges, True)
        handler = FeatureParser(feature_callback)
        parser.setContentHandler(handler)
        parser.setErrorHandler(DiscardErrorHandler(parser))
        parser.parse(input_file)
