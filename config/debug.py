ENV = "development"
DEBUG = True
# a default secret that should be overridden by instance config
SECRET_KEY = "dev"
# E-mail settings
TOKEN_SECRET = "itsdangerous"
TOKEN_MAX_AGE = 1800  # in seconds
TOKEN_FROM_EMAIL = "Automat <automat@localhost>"
TOKEN_SMTP_HOST = "localhost"
DATA_FOLDER = "./instance/"
