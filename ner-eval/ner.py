from abc import ABC, abstractclassmethod


class NerInterface(ABC):
    """Named entity recognizer abstract class."""

    @abstractclassmethod
    def recognize_file(self, input_filename: str, output_filename: str,  next_id=0) -> int:
        """Finds named entities in the input file and save the results to the output file.
        Each entity has an ID that starts with next_id."""
        pass
