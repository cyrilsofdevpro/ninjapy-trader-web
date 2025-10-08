"""Alternative WSGI entrypoint for hosting platforms."""
import os
os.environ.setdefault('DISABLE_DASH_RUN', '1')
import importlib
dash_mod = importlib.import_module('dashboard.app')
dash_app = getattr(dash_mod, 'app', dash_mod)
app = getattr(dash_app, 'server', dash_app)
