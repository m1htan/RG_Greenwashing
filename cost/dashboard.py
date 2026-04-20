"""
Lightweight HTTP server for the cost dashboard.

Usage:
    python cost/dashboard.py [--port 8764]

Opens http://localhost:8764 in the browser.
Serves dashboard.html and provides /api/cost-data endpoint.
"""
from __future__ import annotations

import json
import os
import sys
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

COST_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(COST_DIR.parent))

from cost.cost_tracker import get_summary, DEFAULT_COST_LOG


class DashboardHandler(SimpleHTTPRequestHandler):
    """Serve static files from cost/ and provide API endpoint."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(COST_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/cost-data":
            self._serve_cost_data()
        elif parsed.path == "/" or parsed.path == "":
            self.path = "/dashboard.html"
            super().do_GET()
        else:
            super().do_GET()

    def _serve_cost_data(self):
        try:
            summary = get_summary(DEFAULT_COST_LOG)
            payload = json.dumps(summary, ensure_ascii=False, default=str)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(payload.encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def log_message(self, format, *args):
        # Quieter logging
        if "/api/cost-data" not in str(args):
            super().log_message(format, *args)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Cost Dashboard Server")
    parser.add_argument("--port", type=int, default=8764)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    server = HTTPServer(("0.0.0.0", args.port), DashboardHandler)
    url = f"http://localhost:{args.port}"
    print(f"Cost Dashboard: {url}")
    print(f"Cost log file: {DEFAULT_COST_LOG}")
    print("Press Ctrl+C to stop.\n")

    if not args.no_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
