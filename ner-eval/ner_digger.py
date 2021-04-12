import sys

import nametag

if __name__ == "__main__":
    # Check input args
    if len(sys.argv) != 2:
        print(f"Usage {sys.argv[0]} ner_name", file=sys.stderr)
        print("input_file output_file pairs on stdin", file=sys.stderr)
        exit(1)
    ner_name = sys.argv[1]

    if ner_name == "nametag":
        ner = nametag.get_ner()

    for line in sys.stdin:
        input_file, output_file = line.split()
        with open(input_file, "r") as input, open(output_file, "w") as output:
            ner.recognize(input, output)
