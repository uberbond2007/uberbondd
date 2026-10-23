# Operation Phoenix Reactor — Codespace recovery package

Target: Codespace `automatic-fortnight-gx6xxpjjp5pjcwxq9`, repo `uberbond2007/uberbondd`. Extra spend: $0.

## Truth boundary (read first)

This package was built and tested from an **isolated Claude Cloud container, not from the Codespace**. Nothing here proves the Codespace itself is repaired. What is proven is listed under *Verified in the cloud container*; what still needs the Codespace is under *Unverified until run there*.

## Activate (in the Codespace terminal, ~1 minute)

```bash
git fetch origin claude/sharp-goodall-7iyba5 && git checkout claude/sharp-goodall-7iyba5
bash ops/phoenix-reactor/bin/phoenix install     # apt packages, VNC password, ~/.bashrc hook (idempotent)
phoenix ensure && phoenix desktop                # start supervisor, print the private desktop URL
phoenix doctor                                   # baseline: memory, duplicates, claude, browser sandbox
```
(`phoenix` is on PATH in new shells; the first time use the full path above.)

## Claude Code login on the Pro subscription (no API billing)

Root causes found (observed + official docs, `code.claude.com/docs/en/authentication`, `troubleshoot-install`):

1. Login is a **manual-paste flow** in a Codespace: the CLI prints a ~350–500 char URL, you approve in a browser, then paste `code#state` into the *same running process*. The URL is bound to that process's PKCE challenge. A relaunched `claude`, a second attempt, or a code from an older URL is rejected.
2. Narrow terminals hard-wrap the URL; copying from the wrapped text corrupts it (`Invalid OAuth Request`). A code pasted with line breaks or spaces is "invalid".
3. **Auth precedence**: `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_API_KEY`, `apiKeyHelper`, `CLAUDE_CODE_OAUTH_TOKEN` and cloud-provider variables all outrank a subscription login. A stale Codespaces secret silently overrides it and can force API billing.
4. `claude auth status` can report logged-in while API calls fail (reported for `setup-token`), so we verify with a real call.

`phoenix auth-start` runs the login inside a 500-column tmux session (survives dropped terminals), strips the override variables for that process, and writes the intact one-line URL. `phoenix auth-submit` strips whitespace/zero-width characters, rejects a pasted URL or truncated code locally (without killing the login), then waits for `claude auth status`.

```bash
phoenix auth-start            # open the printed URL in Safari while signed in to your Claude Pro account
phoenix auth-submit           # paste the code from the page
phoenix auth-status --verify  # status + one real `claude -p` call (small subscription usage, no API key)
```
Fallback if the browser flow keeps failing: on any device with a working browser run `claude setup-token`, then `phoenix auth-token` here (hidden input; stored 0600). Documented limit: that token cannot start Remote Control sessions or fetch claude.ai connectors. Never use `claude auth login --console` (that is API billing).
`phoenix install` also creates `~/.config/uberbond-phoenix/prefer-subscription`, so new shells `unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN`. Delete that file to opt out.

Update Claude Code: `claude update` (native install) or `npm i -g @anthropic-ai/claude-code@latest` (Node ≥ 22, no sudo). The cloud container runs 2.1.309; the Codespace version is unverified.

## Desktop (noVNC)

Stack: `Xtigervnc` (16-bit colour, localhost-only, VNC password) + `openbox` (no compositor) + `lib/novnc_gateway.py`, supervised by `lib/supervisor.py`. About **96 MiB RSS** total in the test.

* Safari "downloads a file": the stock `websockify --web` already serves correct types in the cloud test, so the origin was probably not the cause; the gateway nevertheless pins `Content-Type`, `Content-Disposition: inline`, `X-Content-Type-Options: nosniff`, redirects `/` to the client, and `smoke.sh` fails if any of that regresses. If Safari still downloads, the fault is in the forwarding layer: confirm port 6080 is **Private**, open `https://<codespace>-6080.app.github.dev/vnc.html` after signing in to GitHub in the same Safari tab, and send me the response headers (`curl -sI` from inside the Codespace vs. from outside).
* Keep it private: gateway and VNC bind to 127.0.0.1; reachability is the Codespaces private port (GitHub-authenticated) plus the VNC password in `~/.config/uberbond-phoenix/vnc.password.txt`.
* Idle disconnects: gateway sends WebSocket heartbeats every 25 s; noVNC auto-reconnects.

## Chat On Steroids / tunnel

The Core install and its launch command are not visible from the cloud, so nothing about them is invented. `phoenix doctor` reports the Chromium sandbox state (unprivileged user namespaces), unresolved shared libraries (`ldd … | grep 'not found'` → the "C++ runtime" failures) and `libstdc++`. To get restart-with-backoff and duplicate protection for Core and the MCP tunnel, copy `examples/cos-core.service.json.example` to `~/.config/uberbond-phoenix/services.d/`, fill in the verified command (and `probePort` if it listens), set `enabled: true`. Credentials are never stored by this package; keep them in Codespaces secrets/env. An ordinary OpenAI API key is not a tunnel credential.
If Chromium needs `--no-sandbox` because user namespaces are blocked, that is a security trade-off acceptable only in this isolated Codespace and should be an explicit flag in the launcher, not a default here.

## Auto recovery

`~/.bashrc` hook (interactive shells) → `phoenix ensure --quiet` → single-instance supervisor (flock) → bounded backoff 1–60 s, 3 failed probes ⇒ restart, size-capped logs in `~/.local/state/uberbond-phoenix/logs`, `status.json`. A Codespace that GitHub stops is not running anything; the stack returns the next time any terminal opens (or on rebuild with `examples/devcontainer.optional.json`).

## iPad lag

Honest limits: the lag is mostly browser-hosted VS Code + a remote desktop on Safari; no script here changes that. What helps at $0: use the desktop only when needed (`phoenix stop` frees the stack), prefer `claude` in a terminal tab or Claude Code on the web (claude.ai/code, which is what built this) over a Codespace desktop, close idle Codespace tabs. Measure with `phoenix doctor` and `phoenix bench` before/after.

## Verified in the cloud container (2026-10-23)

`node --test tests/phoenix-reactor.test.mjs` → 7/7 pass:
* `tests/smoke.sh` (16 checks): cold start healthy; one supervisor despite 5 concurrent `ensure`; one Xtigervnc; correct headers on `/vnc.html`, `/vnc_lite.html`, `/app/ui.js`, `/core/rfb.js`, `/healthz`; `/` redirect; WebSocket upgrade returns the real `RFB 003.008` banner; SIGKILL of Xtigervnc and gateway auto-recovers; crash-looping extra service is isolated and backed off; no password in logs; `stop` leaves no orphans.
* `tests/auth-flow.sh` (9 checks, stub `claude` that wraps the URL at 60 cols): URL re-joined intact, API key stripped from the login process, bad pastes rejected without losing the session, whitespace-laden code accepted.
* Real `claude auth login` observed (isolated HOME) to confirm the manual-paste prompt and URL shape; no credentials were touched.

## Unverified until run in the Codespace

Actual Claude Pro login completing; Safari rendering through the Codespaces proxy; Chat On Steroids Core and tunnel health; before/after lag numbers; behaviour under the Codespace's own image (non-root user: `phoenix install` uses `sudo` for apt).
