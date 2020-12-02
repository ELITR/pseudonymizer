VENV=. venv/bin/activate

FLASK_FLAGS=FLASK_APP=psan FLASK_RUN_HOST=0.0.0.0
POT_HOME=psan/translations

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

# Build
instance:
	mkdir instance

build: venv instance

# Run web
run: build
	$(VENV); $(FLASK_FLAGS) flask run

# Docker
docker-debug:
	docker-compose -f docker-compose.yaml -f docker-compose.debug.yaml up

docker-build: translate
	docker-compose build

docker-clean:
	docker-compose down -v

# Standard staff
clean: docker-clean
	rm -r venv
	rm -r instance

.PHONY: venv, run, build, docker-debug, docker-build, docker-clean, clean
