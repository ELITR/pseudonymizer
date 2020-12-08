Pseudonymization tool
=====================

Installation
-------------

### Windows

- [Install WSL](https://docs.microsoft.com/en-us/windows/wsl/install-win10)
- Install Windows Terminal (optional, needs Windows 10.0.18362.0 or higher)
    - [Download latest msixbundle](https://github.com/microsoft/terminal/releases)
    - `Add-AppxPackage xyz.msixbundle`
- Install Python 3.9 (to Windows)
- Install IDE
    - VSCode
    - [Configure WSL interpret in PyCharm](https://www.jetbrains.com/help/pycharm/using-wsl-as-a-remote-interpreter.html) (optional, works only in PyCharm Professional)
- Install Docker on [WSL 2](https://docs.docker.com/docker-for-windows/wsl/)

### Requirements
 
- make
- docker and docker-compose
- Python 3.6 or newer

Configuration
-------------

PsAn tool uses Flask framework and runs in Python's venv. The venv is usually auto created by make, but you can also create it manually using `make venv`. The app needs PostgreSQL and redis to work correctly, a connection details has to be provided in env variables:

```bash
# Required params
DB_USER=postgres
DB_PASSWORD=postgres
APP_SECRET_KEY=USE_YOUR_SECRET_KEY
DB_NAME=psan_db
# Optional params, not recommended with docker-compose (or make)
DB_HOST=db
CELERY_REDIS=redis://localhost:6379

```

Runtime
-------

You can start application (with PostreSQL) in Docker containers using `docker-compose up` in project root. The _docker-compose_ expects an `.env` file in project root that contains env variables.

- PSAN tool is available on http://localhost:5000/


You can also start the app without using docker with `make run`.

### Debug

Debug mode is started using `make docker-debug`. This configuration enables debug mode on flask and sets runtime code updates using bind mount.

- SQL adminer is available on http://localhost:5050/
