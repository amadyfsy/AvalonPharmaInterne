"""Point d'entrée WSGI — PythonAnywhere / serveurs WSGI."""

import os
import sys

PROJECT_HOME = os.path.dirname(os.path.abspath(__file__))
if PROJECT_HOME not in sys.path:
    sys.path.insert(0, PROJECT_HOME)

from dotenv import load_dotenv

load_dotenv(os.path.join(PROJECT_HOME, '.env'))
os.environ.setdefault('FLASK_CONFIG', 'production')

from run import app as application  # noqa: E402
