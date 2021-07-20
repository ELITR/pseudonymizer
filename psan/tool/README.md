Pseudonymization tool library
===============

This package provides background logic for pseudonymization tasks. The task consists of these steps:

1. Segmentation and tokenization of text.
2. Recognize named entities using Named entity recognizer (NER).
3. Make automatic rules from recognized named entities.
4. Apply known rules to document

You can also use helping APIs in the `controller` module.

NER interface
-------------

The application supports any NER using an API in the `ner` module. An adapter for NameTag2 NER is part of the library.

### NameTag2 NER ###

NameTag2 adapter uses `ufal.nametag` Python bindings to [NameTag library](https://ufal.mff.cuni.cz/nametag/2).

> Straková Jana, Straka Milan, Hajič Jan: Neural Architectures for Nested NER through Linearization. In: Proceedings of the 57th Annual Meeting of the Association for Computational Linguistics, Copyright © Association for Computational Linguistics, Stroudsburg, PA, USA, ISBN 978-1-950737-48-2, pp. 5326-5331, 2019

#### Configuration ####

You have to add the path to a valid model using an environmental variable in the `.env` file in the project root.

```
NER_MODEL=./instance/model.ner # Location of NER language model
```