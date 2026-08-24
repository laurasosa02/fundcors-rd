"""
Production settings. This is the settings module production deployment
uses (see config/wsgi.py).
"""

import os
from urllib.parse import urlparse

from .base import *  # noqa: F401,F403

DEBUG = False

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# The frontend and backend are same-site but different subdomains, so
# "Lax" is sufficient here (no cross-site POSTs are required) and is more
# robust across browsers than "None" (which additionally requires the
# Secure flag and can be blocked/stripped by stricter browser settings).
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365  # one full year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# Email (SMTP)
# EMAIL_PORT and EMAIL_USE_TLS are coerced to int/bool: the SMTP backend
# requires a real int port, and treats any non-empty string (including
# the string "False") as truthy for EMAIL_USE_TLS, so a raw os.environ.get
# would silently misbehave.
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True").strip().lower() in (
    "1",
    "true",
    "yes",
)

# Origin of the separately-built static frontend in production.
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN")

# Without this, Django scopes the csrftoken cookie to the exact host that
# set it (the backend's own subdomain), which makes it invisible to
# document.cookie on the frontend's different subdomain - the frontend JS
# can never read the token it's supposed to echo back in the X-CSRFToken
# header, so every unsafe request made after Django rotates the token
# (e.g. right after login) fails CSRF validation. Widening the cookie to
# the shared parent domain (leading dot = also matches subdomains) fixes
# that. Derived from FRONTEND_ORIGIN's last two domain labels rather than
# hardcoded, e.g. "https://fundcorsrd.com" -> ".fundcorsrd.com".
_frontend_host = urlparse(FRONTEND_ORIGIN).hostname if FRONTEND_ORIGIN else None
if _frontend_host and "." in _frontend_host:
    CSRF_COOKIE_DOMAIN = "." + ".".join(_frontend_host.split(".")[-2:])

CORS_ALLOWED_ORIGINS = [FRONTEND_ORIGIN]
CORS_ALLOW_CREDENTIALS = True

# Required in addition to CORS_ALLOWED_ORIGINS above (that setting only
# controls whether the browser is allowed to read the response; this one
# controls whether Django's CSRF middleware accepts the request at all -
# see the matching comment in dev.py for why both are needed).
CSRF_TRUSTED_ORIGINS = [FRONTEND_ORIGIN]

# Real reCAPTCHA v2 secret key, requested at
# https://www.google.com/recaptcha/admin for the real production domain.
# No test-key fallback here (unlike dev.py) — if this is left unset,
# registration fails closed (see accounts/views.py::_verify_recaptcha),
# which is safer than silently accepting Google's public test key (which
# always passes and therefore provides zero bot protection) in production.
RECAPTCHA_SECRET_KEY = os.environ.get("RECAPTCHA_SECRET_KEY")
