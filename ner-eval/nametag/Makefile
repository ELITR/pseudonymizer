VENV=. venv/bin/activate

# Model
model:
	curl --remote-name-all https://lindat.mff.cuni.cz/repository/xmlui/bitstream/handle/11234/1-3118{/english-conll-140408.zip}
	unzip english-conll-140408.zip 
	cp english-conll-140408/english-conll-140408.ner .

# Python venv environment
venv/bin/activate: requirements.txt
	test -d venv || python3 -m venv venv
	$(VENV); pip install -Ur requirements.txt
	touch venv/bin/activate

venv: venv/bin/activate

setup: venv model

.PHONY: model venv setup
