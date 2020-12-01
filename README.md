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


Configuration
-------------

PsAn tool uses Flask framework and runs in Python's venv. The environment could be created by `make venv`. The app needs PostgreSQL to work correctly, a connection details should be provided in env variables:

```
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=psan_db
APP_SECRET_KEY=USE_YOUR_SECRET_KEY
```

Runtime
-------

You can also start application (with PostreSQL) in Docker containers using `docker-compose up` in project root. The _docker-compose_ expects an `.env` file in project root that contains env variables.

- PSAN tool is available on http://localhost:5000/
- SQL adminer is available on http://localhost:5050/

You can also start the app without docker using `make run`.

### Debug

Debug configuration is enabled by adding these lines to `.env` file:

```
FLASK_ENV=debug
FLASK_DEBUG=1
```
