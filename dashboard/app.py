import sys
from pathlib import Path

# Ensure repository root is on sys.path so sibling packages (core, backtest, etc.) can be imported
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import pandas as pd
import threading
import time
import os
import json

# NOTE: heavy backtest imports (backtrader, run_backtest) are deferred to runtime
# to avoid slowing or blocking the Dash app startup. They are imported inside
# the background thread that runs the backtest.

# 🔹 Initialize Dash
external_stylesheets = ["https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.title = "NinjaPy Trader Dashboard"

def load_price_data():
    """Load intraday CSV (or fallback sample). Returns a DataFrame with a
    datetime index and numeric OHLCV columns. Returns empty DataFrame if not
    available or parseable.
    """
    base = Path(__file__).resolve().parents[1]
    candidates = [
        base / 'data' / 'feeds' / 'intraday.csv',
        base / 'data' / 'processed' / 'sample_data.csv'
    ]

    for p in candidates:
        if p.exists():
            try:
                df = pd.read_csv(str(p), parse_dates=['datetime'])
            except Exception:
                # try without parse_dates then coerce
                df = pd.read_csv(str(p))
                if 'datetime' in df.columns:
                    try:
                        df['datetime'] = pd.to_datetime(df['datetime'])
                    except Exception:
                        pass

            # require OHLC columns
            required = {'open', 'high', 'low', 'close'}
            if not required.issubset(set(df.columns)):
                continue

            # coerce numeric columns
            for c in ['open', 'high', 'low', 'close', 'volume']:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce')

            # ensure datetime exists and set as index
            if 'datetime' in df.columns:
                df = df.dropna(subset=['datetime']).set_index('datetime')
            else:
                # try to interpret index as datetime
                try:
                    df.index = pd.to_datetime(df.index)
                except Exception:
                    pass

            return df.sort_index()

    # nothing found or parseable
    return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])

# 🔹 Layout
app.layout = html.Div([
    html.H1("📊 NinjaPy EMA Breakout Strategy", style={"textAlign": "center"}),

    html.Div(className='container', children=[
        html.Div(className='row', children=[
            html.Div(className='col-md-2', children=[html.Label("EMA Period:"), dcc.Input(id='ema-period', type='number', value=9, min=1, step=1, className='form-control')]),
            html.Div(className='col-md-2', children=[html.Label('Range Start (HH:MM)'), dcc.Input(id='range-start', type='text', value='09:30', className='form-control')]),
            html.Div(className='col-md-2', children=[html.Label('Range End (HH:MM)'), dcc.Input(id='range-end', type='text', value='10:00', className='form-control')]),
            html.Div(className='col-md-1', children=[html.Label('Qty'), dcc.Input(id='qty', type='number', value=1, min=1, step=1, className='form-control')]),
            html.Div(className='col-md-2', children=[html.Label('Profit target'), dcc.Input(id='profit-target', type='number', value=500, className='form-control')]),
            html.Div(className='col-md-2', children=[html.Label('Initial stop'), dcc.Input(id='initial-stop', type='number', value=450, className='form-control')])
        ])
    ]),

    html.Div(className='text-center my-3', children=[
        html.Button('Run Backtest', id='run-backtest', n_clicks=0, className='btn btn-primary'),
        html.Span(id='run-status', style={'marginLeft': '15px', 'fontWeight': 'bold'})
    ]),

    dcc.Graph(id="price-chart"),

    html.H3('Equity Curve'),
    dcc.Graph(id='equity-chart'),
    html.Div(id='download-link-area'),

    html.Div(className='row', children=[
        html.Div(className='col-md-6', children=[html.H3('Signals (live)'), html.Div(id='signals-table')]),
        html.Div(className='col-md-6', children=[html.H3('Executions'), html.Div(id='executions-table')])
    ]),

    html.H3('Backtest Results'),
    html.Div(id='backtest-metrics'),

    # polling interval to refresh CSV displays
    dcc.Interval(id='refresh-interval', interval=3000, n_intervals=0),

    html.Div(id="status", style={"textAlign": "center", "marginTop": "10px", "fontWeight": "bold"})
])


# --- Health endpoint for platform readiness checks ---
try:
    # The underlying Flask server is available as `app.server`
    flask_app = getattr(app, 'server', None)
    if flask_app is not None:
        @flask_app.route('/health')
        def _health():
            return json.dumps({'status': 'ok'}), 200, {'Content-Type': 'application/json'}
        
        @flask_app.route('/download/<path:filename>')
        def _download(filename):
            # prevent path traversal by allowing only exact filenames in repo root that
            # match our backtest_result_*.json pattern
            base = Path(__file__).resolve().parents[1]
            target = base / filename
            try:
                if not target.exists():
                    return (json.dumps({'error': 'not found'}), 404, {'Content-Type': 'application/json'})
                # simple whitelist: filename must start with backtest_result_ and end with .json
                if not (filename.startswith('backtest_result_') and filename.endswith('.json')):
                    return (json.dumps({'error': 'forbidden'}), 403, {'Content-Type': 'application/json'})
                from flask import send_file
                return send_file(str(target.resolve()), as_attachment=True, download_name=filename)
            except Exception as e:
                return (json.dumps({'error': str(e)}), 500, {'Content-Type': 'application/json'})
except Exception:
    pass


def make_price_figure(df_local, ema_period):
    # df_local expected with datetime index
    if df_local is None or df_local.empty:
        fig = go.Figure()
        fig.update_layout(title='No OHLC data available', template='plotly_dark', height=500)
        return fig

    df_local = df_local.copy()
    # If datetime is index, use it as a column for Plotly
    if df_local.index.name is not None:
        df_local = df_local.reset_index()

    if 'datetime' not in df_local.columns and df_local.shape[1] > 0:
        # attempt to infer a datetime-like column
        for c in df_local.columns:
            if 'date' in c.lower() or 'time' in c.lower():
                try:
                    df_local['datetime'] = pd.to_datetime(df_local[c])
                    break
                except Exception:
                    continue

    # final guard
    if 'datetime' not in df_local.columns:
        fig = go.Figure(); fig.update_layout(title='No datetime column found', template='plotly_dark', height=500); return fig

    # compute EMA
    try:
        df_local['EMA'] = pd.to_numeric(df_local['close'], errors='coerce').ewm(span=ema_period, adjust=False).mean()
    except Exception:
        df_local['EMA'] = None

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df_local['datetime'], open=df_local['open'], high=df_local['high'], low=df_local['low'], close=df_local['close'],
        name='Candlestick', increasing_line_color='green', decreasing_line_color='red'
    ))
    if 'EMA' in df_local.columns:
        fig.add_trace(go.Scatter(x=df_local['datetime'], y=df_local['EMA'], mode='lines', name=f'EMA({ema_period})', line=dict(color='blue')))

    fig.update_layout(title=f'EMA Cross Strategy Visualization (EMA={ema_period})', xaxis_title='Time', yaxis_title='Price', template='plotly_dark', height=700)
    return fig


def update_chart_and_status(ema_period):
    df_local = load_price_data()
    fig = make_price_figure(df_local, ema_period)
    status = f"Strategy Loaded with EMA({ema_period}) — {len(df_local)} bars"
    return fig, status


@app.callback(
    Output("price-chart", "figure"),
    Output("status", "children"),
    Input("ema-period", "value")
)
def update_chart(ema_period):
    return update_chart_and_status(ema_period)


### Backtest runner (non-blocking)
running_backtests = {}


def _run_backtest_thread(job_id, data_file, cash, commission, strategy_kwargs=None):
    try:
        running_backtests[job_id] = 'running'
        # Import heavy modules only inside the worker thread
        try:
            from backtest.run_backtest import run_backtest
        except Exception:
            # If import fails, record the error and exit
            running_backtests[job_id] = 'error: failed to import run_backtest'
            return

        # Run with provided strategy_kwargs
        res = run_backtest(data_file, cash=cash, commission=commission, strategy_kwargs=(strategy_kwargs or {}))
        # persist job result
        base = Path(__file__).resolve().parents[1]
        outp = base / f'backtest_result_{job_id}.json'
        try:
            with outp.open('w', encoding='utf8') as f:
                json.dump(res, f)
        except Exception:
            pass
        running_backtests[job_id] = 'completed'
    except Exception as e:
        running_backtests[job_id] = f'error: {e}'


@app.callback(
    Output('run-status', 'children'),
    Input('run-backtest', 'n_clicks'),
    State('ema-period', 'value'),
    State('range-start', 'value'),
    State('range-end', 'value'),
    State('qty', 'value'),
    State('profit-target', 'value'),
    State('initial-stop', 'value')
)
def on_run_backtest(n_clicks, ema_period, range_start, range_end, qty, profit_target, initial_stop):
    if n_clicks is None or n_clicks == 0:
        return ''
    # start background thread to run backtest
    job_id = str(int(time.time()))
    data_file = str(Path(__file__).resolve().parents[1] / 'data' / 'processed' / 'sample_data.csv')
    # prepare strategy kwargs from UI inputs (match strategy param names)
    strategy_kwargs = {
        'ema_period': int(ema_period) if ema_period is not None else 9,
        'start_time': range_start or '09:30',
        'end_time': range_end or '10:00',
        'profit_target': float(profit_target) if profit_target is not None else 500.0,
        'stop_loss': -abs(float(initial_stop)) if initial_stop is not None else -450.0,
        'qty': int(qty) if qty is not None else 1,
    }
    t = threading.Thread(target=_run_backtest_thread, args=(job_id, data_file, 10000, 0.001, strategy_kwargs), daemon=True)
    t.start()
    return f'Backtest started (job {job_id})'


def _read_csv_table(path):
    if not Path(path).exists():
        return html.Div('No data')
    try:
        df_local = pd.read_csv(path)
        # build a simple HTML table
        header = [html.Th(c) for c in df_local.columns]
        rows = []
        for _, r in df_local.tail(50).iterrows():
            rows.append(html.Tr([html.Td(r[c]) for c in df_local.columns]))
        table = html.Table([html.Thead(html.Tr(header)), html.Tbody(rows)], style={'width': '100%', 'overflowX': 'auto'})
        return table
    except Exception as e:
        return html.Div(f'Failed to read {path}: {e}')


@app.callback(
    Output('signals-table', 'children'),
    Output('executions-table', 'children'),
    Output('backtest-metrics', 'children'),
    Output('equity-chart', 'figure'),
    Output('download-link-area', 'children'),
    Input('refresh-interval', 'n_intervals')
)
def refresh_tables(n):
    base = Path(__file__).resolve().parents[1]
    signals_path = base / 'signals_received.csv'
    exec_path = base / 'executions.csv'
    s = _read_csv_table(signals_path)
    e = _read_csv_table(exec_path)
    # show latest backtest result if present
    latest_job = None
    for p in sorted(base.glob('backtest_result_*.json'), reverse=True):
        latest_job = p
        break
    metrics_html = ''
    eq_fig = go.Figure()
    download_area = html.Div()
    if latest_job is not None:
        try:
            with latest_job.open('r', encoding='utf8') as f:
                jr = json.load(f)
            final = jr.get('final_value')
            metrics = jr.get('metrics', {})
            rows = [html.Div(f"Final portfolio: {final}")]
            for k, v in metrics.items():
                rows.append(html.Div(f"{k}: {v}"))
            metrics_html = html.Div(rows)

            # equity plotting
            equity = jr.get('equity') or []
            if isinstance(equity, list) and len(equity) > 0:
                xs = [item.get('datetime') for item in equity]
                ys = [item.get('equity') for item in equity]
                eq_fig.add_trace(go.Scatter(x=xs, y=ys, mode='lines', name='Equity'))
                eq_fig.update_layout(title='Equity Curve', template='plotly_dark', height=400)

            # download link: serve the saved JSON via a Flask endpoint so browsers
            # can download it reliably instead of using a large data URI.
            try:
                fname = latest_job.name
                href = f"/download/{fname}"
                download_area = html.A('Download latest backtest JSON', href=href, className='btn btn-secondary')
            except Exception:
                download_area = html.Div('Failed to build download link')

        except Exception:
            metrics_html = html.Div('Backtest result unreadable')

    return s, e, metrics_html, eq_fig, download_area


if __name__ == "__main__" and os.environ.get('DISABLE_DASH_RUN', '') != '1':
    # When hosting (containers/servers) we should bind to 0.0.0.0 and read the
    # port from the environment so platforms like Heroku/Render/Vercel can set it.
    # Avoid starting the server from the Werkzeug auto-reloader child process
    # which sets WERKZEUG_RUN_MAIN. Only start when not in a reloader child.
    # This makes importing the module safe when DISABLE_DASH_RUN=1 and when
    # running unit tests or in other tooling.
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' and os.environ.get('DISABLE_DASH_RUN', '') == '':
        # reloader child; continue to let run_server handle lifecycle
        pass
    else:
        host = os.environ.get('HOST', '0.0.0.0')
        port = int(os.environ.get('PORT', os.environ.get('HTTP_PORT', 8050)))
        debug_env = os.environ.get('DASH_DEBUG', '')
        debug = False if debug_env == '' else bool(debug_env)
    # prefer run_server which accepts host/port across Dash versions
    try:
        app.run_server(debug=debug, host=host, port=port)
    except Exception:
        # older Dash versions might expose run instead
        try:
            app.run(debug=debug, port=port)
        except Exception as e:
            print('Failed to start Dash app:', e)
    
