"""
Test harness for scripts/transaction_simulator.py

Starts a lightweight local HTTP server to mock the backend `/transactions`
endpoint, generates a small CSV sample, runs the simulator against it, and
prints a short summary.
"""

import csv
import json as jsonlib
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import sys
import types
import urllib.request
import urllib.error
import urllib.parse

# Provide a minimal 'requests' shim (no external dependency required)
_requests = types.ModuleType("requests")


class _Response:
    def __init__(self, status: int, body: bytes):
        self.status_code = status
        self._body = body

    def raise_for_status(self):
        if 400 <= self.status_code:
            raise RuntimeError(f"HTTP error: {self.status_code}")

    def json(self):
        return jsonlib.loads(self._body.decode("utf-8"))


def _post(url: str, json=None, timeout: float | None = None):
    data = None
    headers = {}
    if json is not None:
        # Always send application/json
        payload = json if isinstance(json, (bytes, bytearray)) else jsonlib.dumps(json).encode("utf-8")
        data = payload
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        return _Response(getattr(resp, "status", 200), body)


_requests.post = _post
sys.modules["requests"] = _requests

# Now import the simulator which expects 'requests'
sys.path.append(str(Path(__file__).resolve().parent.parent))
from scripts.transaction_simulator import TransactionSimulator


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802 (http.server API)
        if self.path != "/transactions":
            self.send_response(404)
            self.end_headers()
            return

        # Read and ignore body; just validate JSON-ish content length
        try:
            length = int(self.headers.get("Content-Length", 0))
        except Exception:
            length = 0
        if length:
            _ = self.rfile.read(length)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        task_id = str(uuid.uuid4())
        self.wfile.write(jsonlib.dumps({"task_id": task_id}).encode("utf-8"))

    # Silence default logging to keep output tidy
    def log_message(self, format, *args):  # noqa: A003
        return


def _start_server(port: int):
    server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _write_sample_csv(path: Path):
    headers = [
        "transaction_type",
        "amount",
        "currency",
        "sender_account",
        "sender_country",
        "receiver_account",
        "receiver_country",
        "purpose",
        "timestamp",
        "jurisdiction",
    ]
    rows = [
        ["transfer", "100.50", "USD", "ACC123", "US", "ACC999", "GB", "invoice", "2024-10-01T12:00:00Z", "US"],
        ["payment", "2500", "EUR", "ACC124", "DE", "ACC998", "FR", "salary", "2024-10-02T09:30:00Z", "DE"],
        ["transfer", "75.00", "HKD", "ACC125", "HK", "ACC997", "HK", "gift", "2024-10-03T18:45:00Z", "HK"],
        ["transfer", "0", "USD", "", "HK", "", "US", "", "", "HK"],
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for r in rows:
            writer.writerow(r)


def main():
    port = 8010
    server = _start_server(port)
    try:
        # Give server a moment to bind
        time.sleep(0.1)

        # Prepare sample CSV
        sample_csv = Path("tmp/test_transactions.csv")
        _write_sample_csv(sample_csv)

        # Run simulator with small batch and no delay
        sim = TransactionSimulator(api_base_url=f"http://127.0.0.1:{port}")
        sim.simulate(csv_path=str(sample_csv), batch_size=2, delay=0.0)

        print("\nOK: Simulator ran against mock backend.")
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
