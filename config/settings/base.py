"""
Base Django settings for the FUNDCORSRD backend, shared by every
environment. Environment-specific settings (dev.py, prod.py) import
everything from this module with ``from .base import *`` and then
override/extend what they need.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR is backend/ (three parents up from this file:
# config/settings/base.py -> config/settings -> config -> backend).
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
# The secret key is never hard-coded here. It must be supplied via the
# DJANGO_SECRET_KEY environment variable. Fail loudly and immediately if
# it's missing instead of silently falling back to an insecure default.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "The DJANGO_SECRET_KEY environment variable is not set. Refusing "
        "to start with no (or a hard-coded) secret key. Set "
        "DJANGO_SECRET_KEY in the environment before running Django."
    )


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "axes",
    "accounts",
    "stations",
    "downloads",
    "inscripciones",
]

AUTH_USER_MODEL = "accounts.User"

# django-axes adds a login-attempt-tracking backend in front of Django's
# default ModelBackend. AxesStandaloneBackend must be listed first so it
# gets a chance to block a locked-out login before ModelBackend even
# checks the password.
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Must sit immediately after SecurityMiddleware per whitenoise docs.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # Must sit above CommonMiddleware per django-cors-headers docs.
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
    # Must be last per django-axes docs.
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Needed for the Django admin UI templates.
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES_DIR = BASE_DIR / "data"
# SQLite creates the database file itself, but not its containing
# directory -- that must exist before the DB is opened, so create it
# eagerly here (idempotent) rather than relying on it having been created
# out-of-band by some other step.
DATABASES_DIR.mkdir(parents=True, exist_ok=True)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATABASES_DIR / "db.sqlite3",
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
    {
        # Custom: requires at least one uppercase letter, one lowercase
        # letter, and one digit. See accounts/password_validators.py.
        "NAME": "accounts.password_validators.ComplexityValidator",
    },
]

# Argon2 first, Django's defaults remain after it as fallbacks (e.g. for
# verifying/upgrading existing PBKDF2 hashes). Requires the argon2-cffi
# package, which a later task adds to requirements.txt.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "es-do"

TIME_ZONE = "America/Santo_Domingo"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/
# These serve the Django admin's own static assets (and any other
# app-bundled static assets) via `collectstatic`.

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Serves static files directly from the WSGI app with compression and
# cache-busting hashed filenames, no separate static file server needed.
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# reCAPTCHA v2 ("I'm not a robot") — verified server-side against Google's
# siteverify endpoint before a registration is accepted (see
# accounts/views.py::_verify_recaptcha). Only the secret key is needed
# here; the public site key lives in the frontend's config.js (site keys
# are meant to be publicly visible in page source, only the secret must
# stay server-side). No default here — dev.py and prod.py each set their
# own appropriate value.
RECAPTCHA_SECRET_KEY = os.environ.get("RECAPTCHA_SECRET_KEY")


# Email
# Registration/approval notification emails are sent "from" this address.
DEFAULT_FROM_EMAIL = "fundcorsrd@gmail.com"

# Where new-registration notification emails are sent for admin review.
ADMIN_NOTIFY_EMAIL = os.environ.get("ADMIN_NOTIFY_EMAIL", "fundcorsrd@gmail.com")


# Descargas Autorizadas (gated download links)
# Each url is read from its own environment variable, falling back to the
# current real link, so a link can be rotated (e.g. a Dropbox share link
# expires or is replaced) without a code change/deploy. This is the
# documented mitigation for these being external, unsigned share links
# rather than links this backend controls/signs itself.
DOWNLOAD_LINKS = [
    {
        "label": "Datos RINEX",
        "description": "Directorio de observables RINEX del servidor institucional",
        "url": os.environ.get("DOWNLOAD_URL_RINEX", "http://rinex.hairo.net.do/CORS/"),
    },
    {
        "label": "Mapa Manzanero DN",
        "description": "Cartografia catastral del Distrito Nacional",
        "url": os.environ.get(
            "DOWNLOAD_URL_MANZANERO",
            "https://www.dropbox.com/scl/fi/38y7qwgaq0ijxza2fodqh/Mapa-Manzanero-DN.dwg?rlkey=qqdfilwkfixlbbs4sx4z5yyui&dl=0",
        ),
    },
    {
        "label": "Soluciones Red FC",
        "description": "Archivos de solucion de la Red FC para post-proceso",
        "url": os.environ.get(
            "DOWNLOAD_URL_SOLUCIONES",
            "https://www.dropbox.com/scl/fo/ovoif0ldwc9dabzpofhj4/APZw8GOGJ4hJVByWFUFhg-0?rlkey=8zimaxys12qwutss1dkskmt3j&dl=0",
        ),
    },
    {
        # NOTE: this label must match the frontend row's .label text in
        # frontend/src/index.html exactly (js/modules/downloads.js matches
        # rows by exact label text to refresh their href) - it previously
        # read "Hojas Topograficas..." (missing the accent the frontend
        # has), which meant this row's href never actually got populated
        # and stayed on its disabled "#" placeholder for every user.
        "label": "Hojas Topográficas Georreferenciadas",
        "description": "Cartografia topografica de referencia del territorio nacional",
        "url": os.environ.get(
            "DOWNLOAD_URL_HOJAS",
            "https://www.dropbox.com/scl/fo/tp81vu4iorp2prnycxv5k/ALyiKBqXZLE3xPu4_2aSwuU?rlkey=79m91l9jaxurpo5wrvrdguw5w&dl=0",
        ),
    },
    {
        "label": "Aplicación CORSDist",
        "description": "Aplicacion movil CORSDist para acceso a la red desde el campo",
        "url": os.environ.get(
            "DOWNLOAD_URL_CORSDIST",
            "https://play.google.com/store/apps/details?id=com.carela.hairo.corsdist",
        ),
    },
]


# django-axes (login attempt lockout)
# https://django-axes.readthedocs.io/
# 10 failed attempts locks out the IP for 15 minutes, matching this
# project's documented login rate-limit spec.
AXES_FAILURE_LIMIT = 10
AXES_COOLOFF_TIME = 0.25  # 15 minutes, expressed in hours
AXES_LOCKOUT_PARAMETERS = ["ip_address"]


# django-csp (Content-Security-Policy header)
# https://django-csp.readthedocs.io/
# django-csp 4.x dict-based configuration format.
# NOTE: this only protects the Django Admin pages this backend renders
# itself (this backend otherwise serves JSON only). The separately-built
# static frontend is not served by this process and needs its own
# equivalent CSP applied as a real HTTP header at deploy time (e.g. via
# the Network Solutions or Apache static hosting config) -- see the final
# task report for this gap.
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "script-src": ["'self'", "https://unpkg.com"],
        "style-src": ["'self'", "https://unpkg.com", "https://fonts.googleapis.com"],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "img-src": [
            "'self'",
            "data:",
            "https://*.tile.openstreetmap.org",
            "https://unpkg.com",
        ],
        "connect-src": ["'self'"],
        "frame-ancestors": ["'none'"],
        "object-src": ["'none'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
    }
}
