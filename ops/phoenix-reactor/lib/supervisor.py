#!/usr/bin/env python3
"""Lightweight single-instance process supervisor for the Codespace desktop.

Properties (each exercised by tests/smoke.sh):
  * single instance via flock -> `ensure` can be called from every shell safely;
  * restart with bounded exponential backoff (1s .. 60s), backoff resets after 120s healthy;
  * liveness probe per service; 3 consecutive failures -> restart;
  * children run in their own process group and are reaped as a group;
  * no secrets in logs or status.json; logs are size-capped;
  * extra services (Chat On Steroids Core, MCP tunnel, ...) come from
    $PHOENIX_CONF/services.d/*.json -- nothing about them is invented here.
"""
import fcntl
import glob
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request

HOME = os.path.expanduser("~")
STATE = os.environ.get("PHOENIX_STATE", os.path.join(os.environ.get("XDG_STATE_HOME", HOME + "/.local/state"), "uberbond-phoenix"))
CONF = os.environ.get("PHOENIX_CONF", os.path.join(os.environ.get("XDG_CONFIG_HOME", HOME + "/.config"), "uberbond-phoenix"))
LIB = os.path.dirname(os.path.abspath(__file__))
DISPLAY = os.environ.get("PHOENIX_DISPLAY", ":1")
VNC_PORT = int(os.environ.get("PHOENIX_VNC_PORT", "5901"))
WEB_PORT = int(os.environ.get("PHOENIX_WEB_PORT", "6080"))
GEOMETRY = os.environ.get("PHOENIX_GEOMETRY", "1280x800")
LOG_CAP = 5 * 1024 * 1024
BACKOFF_MIN, BACKOFF_MAX, STABLE_AFTER = 1, 60, 120
TICK = float(os.environ.get("PHOENIX_TICK", "2"))


def tcp_ok(port, host="127.0.0.1"):
    try:
        with socket.create_connection((host, port), timeout=1.5):
            return True
    except OSError:
        return False


def x_ok():
    return os.path.exists("/tmp/.X11-unix/X" + DISPLAY.lstrip(":"))


def http_ok(url):
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def builtin_services():
    pw = os.path.join(CONF, "vnc.passwd")
    x_lock = "/tmp/.X%s-lock" % DISPLAY.lstrip(":")
    return [
        {
            "name": "xvnc",
            "cmd": ["Xtigervnc", DISPLAY, "-rfbport", str(VNC_PORT), "-rfbauth", pw, "-geometry", GEOMETRY,
                    "-depth", "16", "-localhost", "yes", "-SecurityTypes", "VncAuth", "-AlwaysShared",
                    "-desktop", "UberBond"],
            "probe": lambda: tcp_ok(VNC_PORT),
            "pre": lambda: _clear_stale_x(x_lock),
        },
        {
            "name": "wm",
            "cmd": ["openbox"],
            "env": {"DISPLAY": DISPLAY},
            "wait": x_ok,
            "probe": lambda: True,
        },
        {
            "name": "gateway",
            "cmd": [sys.executable, os.path.join(LIB, "novnc_gateway.py"), "--listen", str(WEB_PORT), "--vnc-port", str(VNC_PORT)],
            "wait": lambda: tcp_ok(VNC_PORT),
            "probe": lambda: http_ok("http://127.0.0.1:%d/healthz" % WEB_PORT),
        },
    ]


def _clear_stale_x(lock):
    # Only called before *we* start Xtigervnc: a lock whose pid is dead blocks restarts.
    try:
        pid = int(open(lock).read().strip())
        os.kill(pid, 0)
    except (FileNotFoundError, ValueError):
        return
    except ProcessLookupError:
        for p in (lock, "/tmp/.X11-unix/X" + DISPLAY.lstrip(":")):
            try:
                os.remove(p)
            except OSError:
                pass
    except PermissionError:
        pass


def extra_services():
    out = []
    for f in sorted(glob.glob(os.path.join(CONF, "services.d", "*.json"))):
        try:
            d = json.load(open(f))
            if d.get("enabled", True) and isinstance(d.get("cmd"), list) and d.get("name"):
                port = d.get("probePort")
                d["probe"] = (lambda p=port: tcp_ok(p)) if port else (lambda: True)
                d["wait"] = None
                out.append(d)
        except Exception as e:
            log("supervisor", "bad service file %s: %s" % (f, e))
    return out


def log(name, msg):
    os.makedirs(os.path.join(STATE, "logs"), exist_ok=True)
    with open(os.path.join(STATE, "logs", "supervisor.log"), "a") as f:
        f.write("%s [%s] %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), name, msg))


class Svc:
    def __init__(self, d):
        self.d = d
        self.name = d["name"]
        self.proc = None
        self.backoff = BACKOFF_MIN
        self.next_start = 0
        self.started_at = 0
        self.fails = 0
        self.restarts = 0
        self.state = "pending"

    def start(self):
        w = self.d.get("wait")
        if w and not w():
            self.state = "waiting"
            return
        if self.d.get("pre"):
            self.d["pre"]()
        if shutil.which(self.d["cmd"][0]) is None and not os.path.isabs(self.d["cmd"][0]):
            self.state = "missing-binary:" + self.d["cmd"][0]
            self.next_start = time.time() + 30
            return
        logp = os.path.join(STATE, "logs", self.name + ".log")
        os.makedirs(os.path.dirname(logp), exist_ok=True)
        if os.path.exists(logp) and os.path.getsize(logp) > LOG_CAP:
            os.replace(logp, logp + ".1")
        env = dict(os.environ, **{k: str(v) for k, v in self.d.get("env", {}).items()})
        out = open(logp, "ab")
        self.proc = subprocess.Popen(self.d["cmd"], stdout=out, stderr=out, stdin=subprocess.DEVNULL,
                                     env=env, cwd=self.d.get("cwd") or HOME, start_new_session=True)
        self.started_at = time.time()
        self.fails = 0
        self.state = "running"
        log(self.name, "started pid=%d" % self.proc.pid)

    def kill(self):
        if self.proc and self.proc.poll() is None:
            try:
                os.killpg(self.proc.pid, signal.SIGTERM)
                self.proc.wait(timeout=5)
            except Exception:
                try:
                    os.killpg(self.proc.pid, signal.SIGKILL)
                except Exception:
                    pass
        self.proc = None

    def tick(self):
        now = time.time()
        if self.proc is None:
            if now >= self.next_start:
                self.start()
            return
        rc = self.proc.poll()
        if rc is not None:
            log(self.name, "exited rc=%s; restart in %ss" % (rc, self.backoff))
            self.proc = None
            self.state = "backoff"
            self.restarts += 1
            self.next_start = now + self.backoff
            self.backoff = min(self.backoff * 2, BACKOFF_MAX)
            return
        if now - self.started_at > STABLE_AFTER:
            self.backoff = BACKOFF_MIN
        if now - self.started_at > 5:  # grace period for the service to bind
            if self.d["probe"]():
                self.fails = 0
            else:
                self.fails += 1
                if self.fails >= 3:
                    log(self.name, "probe failed 3x; restarting")
                    self.kill()
                    self.restarts += 1
                    self.state = "backoff"
                    self.next_start = now + self.backoff
                    self.backoff = min(self.backoff * 2, BACKOFF_MAX)


def main():
    os.makedirs(STATE, exist_ok=True)
    lock = open(os.path.join(STATE, "supervisor.lock"), "a+")  # never truncate before owning the lock
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("supervisor already running")
        return 0
    lock.seek(0)
    lock.truncate()
    lock.write(str(os.getpid()))
    lock.flush()
    if not os.path.exists(os.path.join(CONF, "vnc.passwd")):
        sys.exit("missing %s/vnc.passwd; run `phoenix install` first" % CONF)
    svcs = [Svc(d) for d in builtin_services() + extra_services()]
    stop = []
    for s in (signal.SIGTERM, signal.SIGINT):
        signal.signal(s, lambda *_: stop.append(1))
    log("supervisor", "up pid=%d display=%s vnc=%d web=%d" % (os.getpid(), DISPLAY, VNC_PORT, WEB_PORT))
    while not stop:
        for s in svcs:
            s.tick()
        st = {"pid": os.getpid(), "updated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "services": {s.name: {"state": s.state, "pid": s.proc.pid if s.proc else None,
                                    "restarts": s.restarts} for s in svcs}}
        tmp = os.path.join(STATE, "status.json.tmp")
        json.dump(st, open(tmp, "w"))
        os.replace(tmp, os.path.join(STATE, "status.json"))
        time.sleep(TICK)
    for s in reversed(svcs):
        s.kill()
    log("supervisor", "stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
