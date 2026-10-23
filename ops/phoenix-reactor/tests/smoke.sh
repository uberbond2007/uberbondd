#!/usr/bin/env bash
# End-to-end smoke for the desktop recovery stack, on throwaway display/ports/state.
# Exit 0 only if every check passes. Needs: Xtigervnc vncpasswd openbox websockify novnc curl python3.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
T="$(mktemp -d)"
export PHOENIX_STATE="$T/state" PHOENIX_CONF="$T/conf" PHOENIX_DISPLAY=":77" PHOENIX_VNC_PORT=5977 PHOENIX_WEB_PORT=6077 PHOENIX_TICK=1
P="$HERE/bin/phoenix"; U="http://127.0.0.1:6077"
fail=0; ok() { echo "PASS $*"; }; bad() { echo "FAIL $*"; fail=1; }
cleanup() { "$P" stop >/dev/null 2>&1; pkill -f "Xtigervnc :77" 2>/dev/null; rm -rf "$T"; }
trap cleanup EXIT
for b in Xtigervnc vncpasswd openbox websockify curl python3; do command -v $b >/dev/null || { echo "SKIP missing $b"; exit 77; }; done
[ -f /usr/share/novnc/vnc.html ] || { echo "SKIP no novnc"; exit 77; }

mkdir -p "$PHOENIX_CONF/services.d" "$PHOENIX_STATE"; printf 'smoketest' | vncpasswd -f >"$PHOENIX_CONF/vnc.passwd"; chmod 600 "$PHOENIX_CONF/vnc.passwd"
# an extra supervised service that crashes on purpose, to prove bounded backoff + isolation
echo '{"name":"crasher","cmd":["bash","-c","exit 3"]}' >"$PHOENIX_CONF/services.d/crasher.json"

for i in 1 2 3 4 5; do "$P" ensure --quiet & done; wait
for _ in $(seq 1 30); do [ "$(curl -s -m 2 -o /dev/null -w '%{http_code}' $U/healthz)" = 200 ] && break; sleep 1; done
[ "$(curl -s -m 2 -o /dev/null -w '%{http_code}' $U/healthz)" = 200 ] && ok "healthz 200 after cold start" || bad "healthz not 200"
sleep 2; n="$(pgrep -fc 'lib/supervisor.py')"; [ "$n" = 1 ] && ok "exactly one supervisor despite 5 concurrent ensure calls" || bad "supervisors=$n"
n="$(pgrep -fc 'Xtigervnc :77')"; [ "$n" = 1 ] && ok "exactly one Xtigervnc" || bad "Xtigervnc=$n"

chk() { # path content-type-prefix
  h="$(curl -s -D- -o /dev/null -m 5 "$U$1")"
  echo "$h" | grep -qi "^content-type: $2" && echo "$h" | grep -qi '^content-disposition: inline' && echo "$h" | grep -qi '^x-content-type-options: nosniff' \
    && ok "headers $1 -> $2 inline nosniff" || { bad "headers $1"; echo "$h" | head -12; }
}
chk /vnc.html "text/html; charset=utf-8"; chk /vnc_lite.html "text/html; charset=utf-8"
chk /app/ui.js "text/javascript"; chk /core/rfb.js "text/javascript"; chk /healthz "application/json"
loc="$(curl -s -D- -o /dev/null -m 5 $U/ | tr -d '\r' | awk 'tolower($1)=="location:"{print $2}')"
case "$loc" in /vnc.html*) ok "/ redirects to $loc";; *) bad "root redirect: '$loc'";; esac
curl -s -m 5 $U/vnc.html | grep -qi '<title>noVNC' && ok "vnc.html body is the noVNC client" || bad "vnc.html body"

python3 - <<PY && ok "WebSocket upgrade reaches VNC server (RFB banner)" || bad "websocket/RFB"
import socket, base64, os, sys
s = socket.create_connection(("127.0.0.1", 6077), timeout=5)
k = base64.b64encode(os.urandom(16)).decode()
s.sendall(("GET /websockify HTTP/1.1\r\nHost: x\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Protocol: binary\r\n\r\n" % k).encode())
buf = b""
while b"RFB 003" not in buf and len(buf) < 4096:
    d = s.recv(4096)
    if not d: break
    buf += d
sys.exit(0 if (b" 101 " in buf.split(b"\r\n")[0] and b"RFB 003" in buf) else 1)
PY

# crash recovery: SIGKILL the VNC server and the gateway; both must return
pkill -9 -f 'Xtigervnc :77'; pkill -9 -f 'novnc_gateway.py --listen 6077'
ok_rec=0; for _ in $(seq 1 40); do [ "$(curl -s -m 2 -o /dev/null -w '%{http_code}' $U/healthz)" = 200 ] && { ok_rec=1; break; }; sleep 1; done
[ $ok_rec = 1 ] && ok "recovered after SIGKILL of Xtigervnc + gateway" || bad "no recovery"
n="$(pgrep -fc 'Xtigervnc :77')"; [ "$n" = 1 ] && ok "still exactly one Xtigervnc after recovery" || bad "Xtigervnc=$n after recovery"
python3 - <<PY && ok "status.json shows restarts recorded and crasher isolated" || bad "status.json"
import json,sys; s=json.load(open("$PHOENIX_STATE/status.json"))["services"]
sys.exit(0 if s["xvnc"]["restarts"]>=1 and s["gateway"]["state"]=="running" and s["crasher"]["restarts"]>=1 else 1)
PY
grep -q 'restart in' "$PHOENIX_STATE/logs/supervisor.log" && ok "restart/backoff logged" || bad "no backoff log"
grep -qi smoketest "$PHOENIX_STATE"/logs/* 2>/dev/null && bad "VNC password leaked to logs" || ok "no password in logs"
"$P" bench

"$P" stop >/dev/null; sleep 2
n="$(pgrep -fc 'Xtigervnc :77|novnc_gateway.py --listen 6077|lib/supervisor.py' || true)"; [ "${n:-0}" = 0 ] && ok "stop leaves no orphan processes" || bad "orphans=$n"
exit $fail
