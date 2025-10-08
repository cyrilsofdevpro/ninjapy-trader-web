"""
Simple built-in HTTP server to receive strategy signals and append them to CSV.
POST /signal expects a JSON body with fields:
  datetime (ISO string), event (ENTRY|EXIT|STOP_MOVE), side (LONG|SHORT), price (float), size (int), reason (optional)

This avoids external dependencies (FastAPI) which can have runtime issues on some Python versions.
"""
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import csv

SIGNAL_FILE = Path(__file__).parent / 'signals_received.csv'


class SimpleSignalHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_GET(self):
        # Health check
        if self.path == '/health':
            self._set_headers(200)
            self.wfile.write(json.dumps({'status': 'ok'}).encode())
            return

        # Return all received signals as JSON
        if self.path == '/signals':
            try:
                signals = []
                if SIGNAL_FILE.exists():
                    with SIGNAL_FILE.open('r', encoding='utf8', newline='') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            # convert types where appropriate
                            try:
                                row['price'] = float(row.get('price')) if row.get('price') not in (None, '') else None
                            except Exception:
                                pass
                            try:
                                row['size'] = int(row.get('size')) if row.get('size') not in (None, '') else None
                            except Exception:
                                pass
                            signals.append(row)
                self._set_headers(200)
                self.wfile.write(json.dumps({'signals': signals}).encode())
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            return

        # If GET /signal was requested, return a helpful 405 explaining usage
        if self.path == '/signal':
            self._set_headers(405)
            example = {
                'message': 'Use HTTP POST to submit signals to /signal',
                'example_curl': "curl -X POST http://127.0.0.1:8000/signal -H 'Content-Type: application/json' -d '{\"datetime\":\"2025-10-07T09:35:00\",\"event\":\"ENTRY\",\"side\":\"LONG\",\"price\":103.25,\"size\":1,\"reason\":\"test\"}'",
                'example_powershell': "Invoke-RestMethod -Method POST -Uri http://127.0.0.1:8000/signal -Body (ConvertTo-Json @{ datetime='2025-10-07T09:35:00'; event='ENTRY'; side='LONG'; price=103.25; size=1; reason='test' }) -ContentType 'application/json'"
            }
            self.wfile.write(json.dumps(example).encode())
            return

        # If path not recognized, return 404
        self._set_headers(404)
        self.wfile.write(json.dumps({'error': 'Not found'}).encode())

    def do_POST(self):
        if self.path != '/signal':
            self._set_headers(404)
            self.wfile.write(json.dumps({'error': 'Not found'}).encode())
            return

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf8')
        try:
            data = json.loads(body)
            # validate minimal fields
            required = ['datetime', 'event', 'side', 'price', 'size']
            if not all(k in data for k in required):
                raise ValueError('Missing required fields')

            # ensure file exists
            if not SIGNAL_FILE.exists():
                with SIGNAL_FILE.open('w', encoding='utf8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['datetime', 'event', 'side', 'price', 'size', 'reason'])

            with SIGNAL_FILE.open('a', encoding='utf8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([data.get('datetime'), data.get('event'), data.get('side'), data.get('price'), data.get('size'), data.get('reason', '')])

            self._set_headers(200)
            self.wfile.write(json.dumps({'status': 'ok'}).encode())
        except Exception as e:
            self._set_headers(400)
            self.wfile.write(json.dumps({'error': str(e)}).encode())


def run_server(host='127.0.0.1', port=8000):
    server = HTTPServer((host, port), SimpleSignalHandler)
    print(f'Signal server listening on http://{host}:{port} - POST /signal')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('Shutting down')
        server.server_close()


if __name__ == '__main__':
    run_server()
