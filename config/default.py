import os

# disable the CDN support for Bootstrap
BOOTSTRAP_SERVE_LOCAL = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_DOMAIN = False  # Don't send session cookie to subdomains
COMMIT_REV = "unknown"
# Secrets
SECRET_KEY = os.environ["APP_SECRET_KEY"]
TOKEN_SECRET = os.environ["APP_SECRET_KEY"]
# PSAN tool
DATA_FOLDER = "./instance/"
RULE_AUTOAPPLY_CONFIDENCE = 1
