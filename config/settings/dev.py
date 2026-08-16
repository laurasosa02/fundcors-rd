"""
Local development settings. Used by default via manage.py so plain
``python manage.py runserver`` works locally without extra environment
variables.
"""

import os

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

# Django's CSRF middleware checks the browser's Origin header against this
# list for any unsafe (POST/etc) request whose Origin doesn't match the
# backend's own origin - separate from, and in addition to, the token
# check itself (Django >= 4.0). Without this, every cross-origin POST
# from the real frontend (register/login/logout/inscripcion) is rejected
# with 403 "Origin checking failed" even with a perfectly valid CSRF
# token/cookie pair - CORS_ALLOWED_ORIGINS above does not cover this, it
# only governs whether the browser is allowed to read the response.
CSRF_TRUSTED_ORIGINS = [
    FRONTEND_ORIGIN,
    "http://127.0.0.1:5500",
]

# Google's published reCAPTCHA v2 TEST keys — these always pass
# verification and are explicitly documented by Google as "use only for
# testing, never in production" (https://developers.google.com/recaptcha/docs/faq).
# The matching site key is the default in frontend/src/js/config.js.
# Real production keys must be requested at
# https://www.google.com/recaptcha/admin for the real domain and set via
# the RECAPTCHA_SECRET_KEY env var in prod (see config/settings/prod.py).
RECAPTCHA_SECRET_KEY = os.environ.get(
    "RECAPTCHA_SECRET_KEY", "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe"
)
