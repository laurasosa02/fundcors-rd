"""
Passenger WSGI entry point.

cPanel-style Passenger-based Python App hosting (e.g. Network Solutions)
looks for a file named exactly `passenger_wsgi.py` at the application
root and imports a module-level WSGI callable named `application` from
it. This file exists purely to satisfy that convention; it delegates to
the real WSGI application in config/wsgi.py.
"""

import os
import sys

# Passenger runs this file from an arbitrary working directory, so make
# sure this file's own directory (the backend project root) is on
# sys.path, at the front, before anything else is imported.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Default to production settings unless the hosting environment already
# set DJANGO_SETTINGS_MODULE itself.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

from config.wsgi import application  # noqa: E402
