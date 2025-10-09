#!/usr/bin/env python3
"""Local launcher for the dashboard app.

Use this script instead of `python dashboard/app.py` to avoid Windows path/quoting
issues. It imports the `dashboard.app` module and calls run_server with sensible
defaults. Works inside the project's venv.

Usage:
  python run_dashboard.py
  # or with an explicit port
  PORT=8050 python run_dashboard.py
"""
import os
import importlib

# Ensure the Dash module doesn't auto-start on import
os.environ.setdefault('DISABLE_DASH_RUN', '1')

# sensible defaults
os.environ.setdefault('HOST', '0.0.0.0')
os.environ.setdefault('PORT', os.environ.get('PORT', '8050'))

def main():
    dash_mod = importlib.import_module('dashboard.app')
    dash_app = getattr(dash_mod, 'app', None)
    if dash_app is None:
        raise SystemExit("dashboard.app doesn't expose a Dash `app` object")

    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '8050'))
    debug = bool(os.environ.get('DASH_DEBUG', ''))

    # Use run_server which is supported across Dash versions
    try:
        dash_app.run_server(host=host, port=port, debug=debug)
    except Exception:
        # fall back to older API
        dash_app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    main()
