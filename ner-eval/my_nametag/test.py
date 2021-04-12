import my_nametag

if __name__ == "__main__":
    ner = my_nametag.get_ner()
    ner.recognize_file("dataset/example.parsed", "nametag.output")
