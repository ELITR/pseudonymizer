VENV=. venv/bin/activate

# Model
stanford-corenlp-4.2.0-models-english.jar:
	wget https://nlp.stanford.edu/software/stanford-corenlp-4.2.0-models-english.jar

stanford-ner-4.2.0.zip:
	wget https://nlp.stanford.edu/software/stanford-ner-4.2.0.zip

stanford-ner: stanford-ner-4.2.0.zip
	unzip stanford-ner-4.2.0.zip 
	cp $(wildcard stanford-ner-????-??-??)/stanford-ner.jar .
	cp $(wildcard stanford-ner-????-??-??)/classifiers/english.all.3class.distsim.crf.ser.gz .

model: stanford-corenlp-4.2.0-models-english.jar
	python3 -m nltk.downloader punkt

# Python venv environment
venv/bin/activate: requirements.txt
	test -d venv || python3 -m venv venv
	$(VENV); pip install -Ur requirements.txt
	touch venv/bin/activate

venv: venv/bin/activate

setup: venv model

.PHONY: model venv setup
