VENV=. venv/bin/activate

model:
	$(VENV); python3 -m spacy download en_core_web_sm

# Python venv environment
venv/bin/activate: requirements.txt
	test -d venv || python3 -m venv venv
	$(VENV); pip install -Ur requirements.txt
	touch venv/bin/activate

venv: venv/bin/activate

setup: venv model

.PHONY: model venv setup
