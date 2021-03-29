VENV=. venv/bin/activate

# Python venv environment
venv/bin/activate: 
	test -d venv || python3 -m venv venv
	touch venv/bin/activate

venv: venv/bin/activate

setup: venv
	$(VENV); $(MAKE) -C nametag
	$(VENV); $(MAKE) -C nltk
	$(VENV); $(MAKE) -C spacy

clean:
	rm -r venv

.PHONY: venv clean