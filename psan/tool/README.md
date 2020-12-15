Pseudomize tool
===============

This package provides background logic for psedomize task. The task consists of these steps:

1. Recognize named entities using Named entity recognizer (NER). These named entities are than called candidates.
2. Every candidate is annotated. User decides if a candidate is private or not.
3. Private candidates are hashed.

NER interface
-------------

Application supports two NER algorithms:

- Regex NER
- NameTag2 NER
- External tool NER
- or any class that implements `Ner` from `psan.tool` package

### NameTag2 NER ###

NameTag2 adapter uses `ufal.nametag` Python bindings to [NameTag library](https://ufal.mff.cuni.cz/nametag/2).

> Straková Jana, Straka Milan, Hajič Jan: Neural Architectures for Nested NER through Linearization. In: Proceedings of the 57th Annual Meeting of the Association for Computational Linguistics, Copyright © Association for Computational Linguistics, Stroudsburg, PA, USA, ISBN 978-1-950737-48-2, pp. 5326-5331, 2019

#### Configuration ####

You have to add this variable to `.env` file.

```
NER_MODEL=./model.ner # Location of NER language model
```