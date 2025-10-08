"""WSGI entrypoint for Render / gunicorn compatibility.

This exposes the Flask WSGI app as `app`, which allows commands like
`gunicorn app:app` to work. It simply imports the Dash app module and
re-exports the underlying Flask server.
"""
import os

# Ensure we don't start the Dash development server on import
os.environ.setdefault('DISABLE_DASH_RUN', '1')

import importlib

# Import the dashboard.app module and extract the Dash instance named `app`
dash_mod = importlib.import_module('dashboard.app')
try:
	dash_app = getattr(dash_mod, 'app')
except Exception:
	# if the module defines a different symbol, fall back to the module itself
	dash_app = dash_mod

# Expose the Flask WSGI app for Gunicorn
app = getattr(dash_app, 'server', dash_app)

# optional: expose the Dash instance too
dash = dash_app
