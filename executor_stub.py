"""
Executor stub: receives signals (either via HTTP POST or by reading signals CSV) and logs 'executions' to a file.
This is a template for hooking real broker APIs like Alpaca, Interactive Brokers, etc.
"""
import csv
from pathlib import Path
import time
import csv

EXEC_FILE = Path(__file__).parent / 'executions.csv'
SIGNAL_FILE = Path(__file__).parent / 'signals_received.csv'


# simple function to write an execution record
def log_execution(sig: dict, status: str = 'ACK'):
    if not EXEC_FILE.exists():
        with EXEC_FILE.open('w', encoding='utf8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['datetime', 'event', 'side', 'price', 'size', 'reason', 'status', 'ts'])
    with EXEC_FILE.open('a', encoding='utf8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([sig.get('datetime'), sig.get('event'), sig.get('side'), sig.get('price'), sig.get('size'), sig.get('reason', ''), status, time.time()])

# Example: poll the signals file and 'execute' them locally
def poll_and_execute():
    if not SIGNAL_FILE.exists():
        print('No signals file found')
        return
    with SIGNAL_FILE.open('r', encoding='utf8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sig = dict(row)
            # normalize types
            try:
                sig['price'] = float(sig.get('price', 0))
            except Exception:
                sig['price'] = 0.0
            try:
                sig['size'] = int(float(sig.get('size', 0)))
            except Exception:
                sig['size'] = 0
            print('Executing:', sig)
            # Here you would call broker API; we just log
            log_execution(sig, status='EXECUTED')

if __name__ == '__main__':
    poll_and_execute()

# Placeholder: how to forward signals to this executor via HTTP in the signal_server
# requests.post('http://127.0.0.1:9000/exec', json=signal_json)

# TODO: Add an HTTP endpoint to accept signals directly and execute via broker API
