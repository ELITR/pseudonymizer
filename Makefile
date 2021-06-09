VENV=. venv/bin/activate

POT_HOME=psan/translations
FLAKE_BIN=venv/bin/flake8

# Python venv environment
venv/bin/activate: requirements.txt
	test -d venv || python3 -m venv venv
	$(VENV); pip install -Ur requirements.txt
	touch venv/bin/activate

$(FLAKE_BIN): requirements-debug.txt venv
	$(VENV); pip install -Ur requirements-debug.txt
	touch $(FLAKE_BIN)

venv: $(VENV)

venv-debug: $(VENV) $(FLAKE_BIN)

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

setup: venv instance

# Run web
run: setup translate
	./run_web.sh

test: setup
	./run_web.sh

# Docker
docker-run:
	docker-compose up

docker-debug: instance
	echo "COMMIT_REV = \"bind-mount\""  > ./instance/config.py
	docker-compose -f docker-compose.yaml -f docker-compose.debug.yaml up --abort-on-container-exit
	
docker-test: instance
	echo "COMMIT_REV = \"bind-mount-testing\""  > ./instance/config.py
	docker-compose -f docker-compose.yaml -f docker-compose.test.yaml up --abort-on-container-exit --exit-code-from flask

docker-build: instance translate
	echo "COMMIT_REV= \"$(shell git rev-parse HEAD)\""  > ./instance/config.py
	docker-compose build

docker-clean:
	docker-compose down -v

# Debug
lint: venv-debug
	$(VENV); flake8 . --count --select=E9,F63,F7,F82,H306,H301 --show-source --statistics
	$(VENV); flake8 . --exit-zero --statistics

bandit: venv-debug
	$(VENV); bandit psan -r

# Standard staff
clean: docker-clean
	rm -r venv
	rm -r instance

.PHONY: venv, venv-debug, setup, run, test, docker-debug, docker-build, docker-test, docker-clean, lint, bandit, clean
