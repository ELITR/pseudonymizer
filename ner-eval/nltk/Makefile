.DEFAULT_GOAL := setup

# Model
stanford-corenlp-4.2.0-models-english.jar:
	wget https://nlp.stanford.edu/software/stanford-corenlp-4.2.0-models-english.jar

stanford-ner-4.2.0.zip:
	wget https://nlp.stanford.edu/software/stanford-ner-4.2.0.zip

stanford-ner: stanford-ner-4.2.0.zip
	unzip stanford-ner-4.2.0.zip 
	cp $(wildcard stanford-ner-????-??-??)/stanford-ner.jar .
	cp $(wildcard stanford-ner-????-??-??)/classifiers/english.all.3class.distsim.crf.ser.gz .

venv: requirements.txt
	pip install -Ur requirements.txt

model: stanford-corenlp-4.2.0-models-english.jar
	python3 -m nltk.downloader punkt

setup: venv model

.PHONY: model venv setup
