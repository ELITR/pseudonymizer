VENV=. venv/bin/activate

# Python venv environment
venv/bin/activate: requirements.txt
	test -d venv || python3 -m venv venv
	$(VENV); pip install -Ur requirements.txt
	touch venv/bin/activate

venv: venv/bin/activate

setup: venv
	$(VENV); $(MAKE) -C my_nametag
	$(VENV); $(MAKE) -C my_nltk
	$(VENV); $(MAKE) -C my_spacy

clean:
	rm -r venv
	rm *.output

notebook: venv
	$(VENV); jupyter-notebook --ip $(shell hostname -I) --no-browser .

test:
	$(VENV); PYTHONPATH=. python3 my_nametag/test.py
	test -e nametag.output

.PHONY: venv clean test notebook
