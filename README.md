Pseudonymization tool
=====================

Web-based tool for data de-identification.

Requirements
------------

### Windows

- [Install WSL](https://docs.microsoft.com/en-us/windows/wsl/install-win10)
- Install [Windows Terminal](https://github.com/microsoft/terminal) (optional, needs Windows 10.0.18362.0 or higher)
- Install Python 3.7 (to Windows)
- Install IDE (optional)
    - VSCode
    - [PyCharm with WSL interpret](https://www.jetbrains.com/help/pycharm/using-wsl-as-a-remote-interpreter.html) (works only in PyCharm Professional)
- Install Docker on [WSL 2](https://docs.docker.com/docker-for-windows/wsl/)

### Dependencies

- make
- docker and docker-compose
- Python 3.7

Pseudonymization tool uses Flask framework and runs in Python's venv. The venv is usually auto created by make, but you can also create it manually using `make venv`.

Configuration
-------------

The app needs PostgreSQL and Redis to work correctly, a connection details has to be provided in env variables:

```bash
# Required params
DB_USER=postgres
DB_PASSWORD=postgres
APP_SECRET_KEY=USE_YOUR_SECRET_KEY
# Optional params, not recommended with docker-compose (or make)
DB_HOST=db
DB_NAME=psan_db
CELERY_REDIS=redis://localhost:6379

```

Runtime
-------

The application expects the `.env` file in the project root that contains the configuration.

- PSAN tool is available on http://localhost:5000/
- SQL adminer is available on http://localhost:5050/ (only in debug)

### Debug runtime

You can start the application in debug mode (with PostreSQL and Redis) in Docker containers using `make docker-debug`. This configuration enables debug mode in flask and sets runtime code updates using bind mount.

### Tests

The repository has some unit tests in folder `tests`. These tests could be executed using `make docker-test` or without docker (in _venv_) using `run_tests.sh` in the project root.

### Production

You can start the application (with PostreSQL and Redis) in Docker containers using `docker-compose up` in the project root. You can also start the app without using docker (in _venv_) using `run.sh`.
