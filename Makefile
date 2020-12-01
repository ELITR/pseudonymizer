VENV=. venv/bin/activate

FLASK_FLAGS=FLASK_APP=psan FLASK_ENV=debug FLASK_DEBUG=1 FLASK_RUN_HOST=0.0.0.0

# Python venv environment
$(VENV): requirements.txt
	test -d venv || python3 -m venv venv
	$(VENV); pip install -Ur requirements.txt
	touch venv/bin/activate

venv: $(VENV)

# Translations
# Extract strings for translation
$(POT_HOME)/base.pot: babel.cfg $(shell find . -name "*.py" -o -name "*.html") venv
	test -d $(POT_HOME) || mkdir $(POT_HOME)
	$(VENV); pybabel extract -F babel.cfg -k lazy_gettext -o $(POT_HOME)/base.pot .

# Create or update Czech translation
$(POT_HOME)/cs/LC_MESSAGES/messages.po: $(POT_HOME)/base.pot venv
	test -d $(POT_HOME)/cs || ($(VENV); pybabel init -i $(POT_HOME)/base.pot -d $(POT_HOME) -l cs)
	test -d $(POT_HOME)/cs && ($(VENV); pybabel update -i $(POT_HOME)/base.pot -d $(POT_HOME))

# Compile translation
%.mo: %.po
	$(VENV); pybabel compile -d $(POT_HOME)

translate: $(POT_HOME)/cs/LC_MESSAGES/messages.mo

# Runtime
instance:
	mkdir instance

# Run
run: venv instance
	$(VENV); $(FLASK_FLAGS) flask run


# Build (called by deploy scripts)
build: venv 

# Standard staff
clean:
	rm -r venv
	rm -r instance

.PHONY: venv, run, build, clean
