.DEFAULT_GOAL := setup

# Model
model:
	curl --remote-name-all https://lindat.mff.cuni.cz/repository/xmlui/bitstream/handle/11234/1-3118{/english-conll-140408.zip}
	unzip english-conll-140408.zip 
	cp english-conll-140408/english-conll-140408.ner .

venv: requirements.txt
	pip install -Ur requirements.txt

setup: venv model

.PHONY: model venv setup