NinjaPy Trader — Dashboard & Backtest

Quick start

1) Create a virtualenv and install dependencies:

   python -m venv venv
   & venv\Scripts\Activate.ps1
   pip install -r requirements.txt

2) Start the dashboard (foreground so you can see logs):

   & 'C:/Users/Cyril Sofdev/Documents/Weather App/venv/Scripts/python.exe' -c "import importlib,traceback,sys
   try:
       m=importlib.import_module('dashboard.app')
       print('Starting dashboard on http://127.0.0.1:8050')
       m.app.run(debug=True, port=8050)
   except Exception:
       traceback.print_exc()
       sys.exit(1)"

3) Open the dashboard in your browser:

   Start-Process 'http://127.0.0.1:8050'

Files of interest

- `dashboard/app.py` — Dash UI and runner for backtests
- `backtest/run_backtest.py` — Backtrader runner used by the dashboard
- `core/fractal_model_pro.py` — Converted indicator + example strategy

Notes

- The dashboard will poll for `backtest_result_*.json` files created by backtests and display metrics/equity.
- For production/broker execution, implement a proper executor bridge — the current executor is a simulation stub.

Deploying to Render.com
----------------------

There are two easy options to deploy this app on Render: Docker (recommended) or Native (Gunicorn).

1) Docker (recommended)

   - Render will build the included `Dockerfile`. Ensure your repo is connected to Render and the `render.yaml` manifest
     (included) points to this service. The `Dockerfile` exposes port 8050 and runs `gunicorn` against `dashboard.app:app.server`.

   - In Render dashboard: New -> Web Service -> Connect repo -> Use Docker -> set branch `main` -> Deploy.

2) Native/Python (Gunicorn)

   - If you prefer Render's native Python builder, remove or ignore the Docker option and set the start command to:

       gunicorn -b 0.0.0.0:$PORT dashboard.app:app.server

   - Make sure `requirements.txt` includes `gunicorn` (it does). Set the build and start commands in the Render UI and deploy.

Notes and tips
 - Use environment variables in Render to set `PORT`, `HOST`, or `DASH_DEBUG` as needed.
 - For small workloads use the free Starter plan; for production use a larger plan and enable health checks.
 - If you want automatic updates, enable deploy on push for the `main` branch in Render.

