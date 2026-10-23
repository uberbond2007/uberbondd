# PHOENIX checkpoint — Operation Phoenix Reactor (2026-10-23)

Class: INTERNAL_ENGINEERING_RECEIPT. Not proof the Codespace is repaired.

Access reality: session ran in an isolated Claude Cloud container (hostname `vm`, no `CODESPACE_NAME`). The Codespace `automatic-fortnight-gx6xxpjjp5pjcwxq9` was never reachable; nothing in it was inspected or changed.

Delivered: `ops/phoenix-reactor/` (CLI, supervisor, noVNC gateway, Claude login recovery, tests, runbook) and `tests/phoenix-reactor.test.mjs`.

Evidence: `node --test tests/phoenix-reactor.test.mjs` 7/7; `node scripts/check-syntax.mjs` 2966 files parse; desktop stack ≈96 MiB RSS.

Defects found by the tests and fixed before commit: supervisor lock file truncated by a losing instance (orphaned supervisors); vacuous orphan check from an invalid `pgrep` flag.

Findings: stock websockify serves correct headers (Safari download cause not reproduced at origin; gateway pins headers regardless); Claude login is a PKCE manual-paste flow whose URL wraps in narrow terminals; env overrides outrank subscription login.

Blockers (external): Codespace terminal access; owner's Claude Pro browser approval and code paste; Chat On Steroids Core launch command/credentials (not visible from cloud).

Exact next action (owner, one step): in the Codespace terminal run the "Activate" block in `ops/phoenix-reactor/README.md`, then `phoenix doctor` and send the output.
