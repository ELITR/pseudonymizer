from ner import NerInterface

from nametag.adapter import NameTag


def get_ner() -> NerInterface:
    return NameTag("nametag/english-conll-140408.ner")
