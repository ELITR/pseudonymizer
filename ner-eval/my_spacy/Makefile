.DEFAULT_GOAL := setup

model:
	python3 -m spacy download en_core_web_sm

# Python venv environment
venv: requirements.txt
	pip install -Ur requirements.txt

setup: venv model

.PHONY: model venv setup