import time, json
from pathlib import Path
from backtest.run_backtest import run_backtest

job_id = str(int(time.time()))
# repo root (directory containing this script)
base = Path(__file__).resolve().parent
try:
	res = run_backtest(str(base / 'data' / 'processed' / 'sample_data.csv'))
except Exception as e:
	res = {'error': str(e)}
outp = base / f'backtest_result_{job_id}.json'
with outp.open('w', encoding='utf8') as f:
	json.dump(res, f, default=str, indent=2)
print('Wrote', outp)
