#!/usr/bin/env bash
# Drives `phoenix auth-start` / `auth-submit` against a stub `claude` that behaves like the real CLI:
# prints a ~500-char authorize URL hard-wrapped at 60 columns, then waits for "code#state" on stdin.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
command -v tmux >/dev/null && command -v node >/dev/null || { echo "SKIP tmux/node missing"; exit 77; }
T="$(mktemp -d)"; trap 'tmux kill-session -t phoenix-auth-test 2>/dev/null; rm -rf "$T"' EXIT
mkdir -p "$T/bin"
cat >"$T/bin/claude" <<'STUB'
#!/usr/bin/env bash
S="${STUB_STATE:?}"
case "$1 $2" in
  "auth login")
    [ -z "${ANTHROPIC_API_KEY:-}" ] || { echo "STUB: API key leaked into login" >"$S/err"; exit 9; }
    u="https://claude.com/cai/oauth/authorize?code=true&client_id=9d1c250a-e61b-44d9-88ed-5944d1962f5e&response_type=code&redirect_uri=https%3A%2F%2Fplatform.claude.com%2Foauth%2Fcode%2Fcallback&scope=user%3Ainference&code_challenge=d6baGXnPutZ8bUFTsALwTqEvhSbyXRryYbmGV2XbRBk&code_challenge_method=S256&state=przkCXhcyuMvj1V29leh-eYC8CjI8izN-chP-DR3sZw"
    echo "Opening browser to sign in…"; echo "If the browser didn't open, visit: ${u:0:30}"; echo "${u:30}" | fold -w 60
    printf 'Paste code here if prompted > '; read -r c
    [ "$c" = "$STUB_CODE" ] && touch "$S/loggedin" || echo "OAuth error: Invalid code" ;;
  "auth status") [ -f "$S/loggedin" ] && { echo "Logged in (claude.ai)"; exit 0; } || { echo "Not logged in"; exit 1; } ;;
esac
STUB
chmod +x "$T/bin/claude"
export PATH="$T/bin:$PATH" STUB_STATE="$T" STUB_CODE="abcDEF0123456789abcDEF0123456789#stateSTATE0123456789xyz"
export PHOENIX_STATE="$T/state" PHOENIX_CONF="$T/conf" PHOENIX_AUTH_SESSION=phoenix-auth-test ANTHROPIC_API_KEY="sk-ant-should-not-reach-login"
P="$HERE/bin/phoenix"; fail=0; ok(){ echo "PASS $*"; }; bad(){ echo "FAIL $*"; fail=1; }

out="$("$P" auth-start 2>&1)"
url="$(cat "$T/state/login-url.txt" 2>/dev/null)"
[ "${#url}" -gt 300 ] && [[ "$url" != *$'\n'* ]] && [[ "$url" == *"state=przkCXhcyuMvj1V29leh-eYC8CjI8izN-chP-DR3sZw" ]] && ok "wrapped URL re-joined into one intact line (${#url} chars)" || bad "url extraction: $out"
[[ "$out" == *"ANTHROPIC_API_KEY"* ]] && ok "env override reported (value not printed)" || bad "no override warning"
[[ "$out" != *"sk-ant-should"* ]] && ok "secret value never printed" || bad "secret leaked"

r="$("$P" auth-submit "https://claude.com/cai/oauth/authorize?x=1" 2>&1)"; [[ "$r" == *PASTED_URL_NOT_CODE* ]] && ok "pasted URL rejected locally" || bad "url-as-code: $r"
r="$("$P" auth-submit "abc" 2>&1)"; [[ "$r" == *TOO_SHORT* ]] && ok "truncated code rejected locally" || bad "short: $r"
tmux has-session -t phoenix-auth-test 2>/dev/null && ok "login process survived rejected pastes (same PKCE session)" || bad "session died"

r="$("$P" auth-submit "$(printf '  %s\n' "${STUB_CODE:0:20}") $(printf '%s\n' "${STUB_CODE:20}")" 2>&1)"
[[ "$r" == *"login accepted"* ]] && ok "code with embedded spaces/newlines sanitised and accepted" || bad "submit: $r"
[ ! -f "$T/err" ] && ok "API key was stripped from the login process" || bad "$(cat "$T/err")"
"$P" auth-submit x >/dev/null 2>&1 && bad "submit without pending login succeeded" || ok "submit without pending login refused"
exit $fail
