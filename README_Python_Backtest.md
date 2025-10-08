Nine EMA Range Breakout (Python / Backtrader)

Overview
- Python/backtest reference implementation of your NinjaTrader rules.
- Captures the high/low during a configurable time window and uses a 9 EMA breakout to enter trades. Includes stop/reverse and break-even stop move behavior.

Files
- `nine_ema_range_breakout.py` — strategy and CLI runner (in this folder).

Requirements
- Python 3.8+
- Install dependencies (from this repo):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

CSV format
- Columns (in order): `datetime,open,high,low,close,volume`
- Datetime must use `YYYY-MM-DD HH:MM:SS` (e.g. `2025-10-07 09:31:00`). The script detects and strips a header line automatically and supports UTF-8/UTF-16/latin-1 encodings.

CLI usage examples
- Basic run:

```powershell
.\.venv\Scripts\python.exe .\nine_ema_range_breakout.py .\data\intraday.csv
```

- Full example with signal export and ticks stops:

```powershell
.\.venv\Scripts\python.exe .\nine_ema_range_breakout.py .\data\intraday.csv --export-signals .\data\signals.csv --stop-mode ticks --tick-size 0.25 --qty 1
```

Key CLI options
- `--range-start` / `--range-end`: range capture window (HH:MM)
- `--profit-target`: profit target (currency or ticks depending on stop-mode)
- `--initial-stop`: initial stop (currency or ticks)
- `--breakeven-plus`: amount to set stop to after reaching profit-target
- `--contract-value`: currency per price unit (useful for futures multipliers)
- `--stop-mode`: `currency` (default) or `ticks`
- `--tick-size`: price per tick when using `--stop-mode ticks`
- `--export-signals`: path to append signals CSV (columns: datetime,event,side,price,size,reason)

Notes
- The script is intended as a backtest/signal generator. To trade live you should either port the final logic back to NinjaTrader C# (I can do that) or implement an execution bridge that reads the exported signals and sends orders to your broker.

If you'd like, I can:
- Port this exact logic to NinjaTrader C# for live strategy use (recommended for direct live trading in NinjaTrader).
- Add commission/slippage, a performance report, or an HTTP signal endpoint.

Running the signal server and executor (all-Python live flow)

1) Install server dependencies and start the server:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\signal_server.py
```

This starts an HTTP server on http://127.0.0.1:8000 that accepts POST /signal with JSON payloads. The Python strategy can be modified to POST signals to this endpoint instead of writing a CSV, or use `--export-signals` and let the server/executor poll the CSV.

2) Run the executor stub to consume `signals_received.csv` and log executions:

```powershell
.\.venv\Scripts\python.exe .\executor_stub.py
```

3) Integration options
- Strategy -> File: use `--export-signals` to append signals to a CSV and run the executor to poll and execute.
- Strategy -> HTTP: modify the strategy Python to POST signals to `http://127.0.0.1:8000/signal` for immediate processing.

Security note: The server provided is a development stub and listens on localhost. For production use, add authentication, HTTPS, request validation and robust error handling before connecting to real broker APIs.

