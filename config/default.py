import os

# disable the CDN support for Bootstrap
BOOTSTRAP_SERVE_LOCAL = True
SESSION_COOKIE_HTTPONLY = True
COMMIT_REV = "unknown"
# Secrets
SECRET_KEY = os.environ["APP_SECRET_KEY"]
TOKEN_SECRET = os.environ["APP_SECRET_KEY"]
