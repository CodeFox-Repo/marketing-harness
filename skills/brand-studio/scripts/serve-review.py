#!/usr/bin/env python3
"""Serve a round-review directory with a save endpoint.

Serves the current dir over HTTP (for round-review.html + round-N.json + images)
and accepts `POST /save?file=decisions-<round>.json`, writing the body next to the
round data so the agent can Read it directly — no copy/paste. Filenames are
restricted to `decisions-*.json` to prevent path traversal.

Usage:
    cd <review-dir>
    python3 serve-review.py [PORT]   # default 8123
"""
from __future__ import annotations

import http.server
import re
import socketserver
import sys
import urllib.parse

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8123
SAVE_NAME = re.compile(r"decisions-[\w.\-]+\.json")


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/save":
            self.send_error(404, "only /save")
            return
        params = urllib.parse.parse_qs(parsed.query)
        filename = (params.get("file") or [""])[0]
        if not SAVE_NAME.fullmatch(filename):
            self.send_error(400, "file must match decisions-*.json")
            return
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        with open(filename, "wb") as handle:
            handle.write(body)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')
        sys.stderr.write(f"saved {filename} ({len(body)} bytes)\n")


def main() -> int:
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"serve-review on http://localhost:{PORT} (GET files, POST /save)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
