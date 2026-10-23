#!/usr/bin/env python3
"""Private noVNC gateway for the UberBond Codespace desktop.

Why this exists instead of a bare `websockify --web`:
  * every response carries an explicit Content-Type, `Content-Disposition: inline`
    and `X-Content-Type-Options: nosniff`, so Safari/iPadOS renders vnc.html
    instead of offering it as a download;
  * `/` redirects to the noVNC client with iPad-friendly defaults;
  * `/healthz` gives the supervisor and the smoke tests a cheap liveness probe;
  * WebSocket heartbeats keep idle sessions alive through the Codespaces proxy;
  * it binds to 127.0.0.1 only. Reachability comes from the Codespaces *private*
    port forward (GitHub-authenticated) plus the VNC password.
"""
import argparse
import json
import os
import socket
import sys
import time

from websockify.websocketproxy import ProxyRequestHandler, WebSocketProxy

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".oga": "audio/ogg",
}
START = time.time()
CLIENT_QUERY = "autoconnect=0&resize=scale&reconnect=1&reconnect_delay=2000&show_dot=1"


class Handler(ProxyRequestHandler):
    vnc_port = 5901

    def guess_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        return CONTENT_TYPES.get(ext, "application/octet-stream")

    def end_headers(self):
        # websockify's upgrade path never reaches here; only plain HTTP does.
        self.send_header("Content-Disposition", "inline")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def _reply(self, code, ctype, body, head_only=False):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if not head_only:
            self.wfile.write(data)

    def do_GET(self):
        self._route(head_only=False)

    def do_HEAD(self):
        self._route(head_only=True)

    def _route(self, head_only):
        path = self.path.split("?", 1)[0]
        upgrade = self.headers.get("upgrade", "").lower()
        if upgrade == "websocket":
            return super().do_GET()
        if path in ("/", "/index.html"):
            self.send_response(302)
            self.send_header("Location", "/vnc.html?" + CLIENT_QUERY)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path == "/healthz":
            vnc_ok = _tcp_ok("127.0.0.1", self.vnc_port)
            body = json.dumps({"ok": vnc_ok, "vnc": vnc_ok, "uptimeSeconds": int(time.time() - START)})
            return self._reply(200 if vnc_ok else 503, "application/json; charset=utf-8", body, head_only)
        return super().do_HEAD() if head_only else super().do_GET()


def _tcp_ok(host, port):
    try:
        with socket.create_connection((host, port), timeout=1.5):
            return True
    except OSError:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen", type=int, default=6080)
    ap.add_argument("--vnc-port", type=int, default=5901)
    ap.add_argument("--web", default="/usr/share/novnc")
    ap.add_argument("--heartbeat", type=int, default=25)
    a = ap.parse_args()
    if not os.path.isfile(os.path.join(a.web, "vnc.html")):
        sys.exit(f"noVNC client not found in {a.web} (install the 'novnc' package)")
    Handler.vnc_port = a.vnc_port
    WebSocketProxy(
        Handler,
        listen_host="127.0.0.1",
        listen_port=a.listen,
        target_host="127.0.0.1",
        target_port=a.vnc_port,
        web=a.web,
        heartbeat=a.heartbeat,
        verbose=False,
    ).start_server()


if __name__ == "__main__":
    main()
