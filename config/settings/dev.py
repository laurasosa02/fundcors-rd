"""
Local development settings. Used by default via manage.py so plain
``python manage.py runserver`` works locally without extra environment
variables.
"""

from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Registration and approval emails just print to the console locally.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Fine over local HTTP (no TLS in development).
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Placeholder origin for the separately-built static frontend during local
# development (e.g. served via VS Code Live Server or similar).
FRONTEND_ORIGIN = "http://localhost:5500"

# Browsers treat localhost and 127.0.0.1 as different origins even though
# they resolve to the same machine, so both variants are allowed here -
# whichever one the frontend dev server actually got opened as.
CORS_ALLOWED_ORIGINS = [
    FRONTEND_ORIGIN,
    "http://127.0.0.1:5500",
]
CORS_ALLOW_CREDENTIALS = True
