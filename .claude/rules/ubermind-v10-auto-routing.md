# UberMind V10 | Automatic Crown Model Routing

For tasks in this repository, keep the current main session as the final reviewer. Prefer Opus for difficult original reasoning, but never claim this rule changes the selected main model or subscription billing route.

Choose the lowest-total-usage route that preserves result quality: first reuse exact verified artifacts or use native reads/tests with no AI subagent. Do not start helpers for trivial tasks. For bounded work needing independent context, proactively delegate to the matching NAMED custom subagent without asking the founder to select models:

- `ubermind-v10-scout`: Haiku LOW (max 6 turns), exact paths, IDs, quick Grep/Glob.
- `ubermind-v10-researcher`: Haiku MEDIUM (max 8 turns), bounded read-only source comparison.
- `ubermind-v10-builder`: Sonnet MEDIUM (max 12 turns), scoped coding, narrow tests.
- `ubermind-v10-falsifier`: Sonnet HIGH (max 8 turns), independent read-only negative tests and strongest fair counterexample.
- `ubermind-v10-strategist`: Opus HIGH (max 8 turns), rare independent difficult EQ/game-theory/business decisions.
- `ubermind-v10-frontier`: Opus XHIGH (max 8 turns), rare original hard unknowns after lower-cost methods prove insufficient.

Default to no parallel helpers or one named agent. Use at most two only if the tasks are truly independent and their expected value exceeds coordination cost. Main Opus Crown sets acceptance criteria for consequential work, reviews evidence, and accepts or rejects the result; do not add a second Opus specialist without reason.

A *native fork* inherits the entire parent conversation and its current model (often Opus). It does NOT automatically switch to Haiku or Sonnet. Use a fork only for context-heavy side work; use the named subagents above for actual per-task model/effort selection.

Project AGENTS.md, CLAUDE.md, legitimate permissions, privacy, rights, source and quality requirements remain binding. This repository is PUBLIC: do not add private 890-idea bodies, 52-doctrine source texts, Ω46 personal material, credentials or PHOENIX records. Claims of retrieved sources require access to the original source. Never auto-send outreach, deploy, trade, buy, create extra credits, use paid API inference, or evade plan limits.

On substantial tasks include a terse **route receipt**: main model actually observed or UNKNOWN; named subagents truly invoked and model/effort observed or UNKNOWN; evidence/tests; subscription usage SAVINGS MEASURED or UNKNOWN. No unmeasured multiplier claims.
