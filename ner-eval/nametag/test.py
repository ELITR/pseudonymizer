import nametag

if __name__ == "__main__":
    ner = nametag.get_ner()
    ner.recognize_file("dataset/example.parsed", "nametag.output")
