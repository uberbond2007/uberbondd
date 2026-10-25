# Lead-Path Revenue Leak Evidence Sprint: white-label demo

All data in this directory is **synthetic**: a fictional agency, client and lead, with `*.example` domains only. There are no dependencies and no external network calls. See [`PILOT_OFFER.md`](PILOT_OFFER.md) for the draft agency pilot.

## What the sprint checks
1. Whether the first outbound human contact (call, SMS or email) reached the lead within the SLA after CRM lead creation.
2. Whether contact-log coverage supports "no earlier contact". There are three coverage classes:
   - `SUPPLIER_DECLARED_COMPLETE`: the channels and window are covered *and* `coverage.declaration` is a valid record with an evidence ID, a declarant, a timestamp with a zone, and a statement. The report shows the declaration and its evidence ID. **The sample is in this class (declaration `EV-DEC-001`). Independent reconciliation was NOT PERFORMED.**
   - `INDEPENDENTLY_RECONCILED_COMPLETE`: used only when `coverage.reconciliation` names who reconciled, when, and against which authoritative-source evidence IDs.
   - `INCOMPLETE_OR_MISSING`: a channel or part of the time window is not covered, or there is neither a valid declaration record nor a valid reconciliation record. The `basis` label alone never counts. The verdict is `UNCONFIRMED_COVERAGE_GAP`.
3. An illustrative gross-margin-at-risk figure from agency-supplied assumptions. It is shown **only** for `CONFIRMED_BREACH`; otherwise `buildReport` returns null amounts and the page shows no amount.

## What the agency provides and gets
The agency provides a CRM export, an intake log, contact logs with a coverage statement, the SLA definition, and optional risk assumptions. It gets a report with the verdict, its basis, the cited evidence IDs and timestamps, the SLA math, the coverage class and the reconciliation status.

## What it can and cannot establish
It can establish timing against the SLA, and whether the stated coverage supports "no earlier contact". It cannot establish realized loss, causal attribution, recovered revenue or any guarantee. It also cannot establish that a supplier's coverage declaration is true unless a reconciliation record exists.

## Reproduce
```
node examples/lead-path-leak-sprint-demo/sprint.mjs                  # report as JSON
node --test examples/lead-path-leak-sprint-demo/sprint.test.mjs      # focused tests
node examples/lead-path-leak-sprint-demo/serve.mjs                   # then open 127.0.0.1:8787/demo.html
```
`demo.html` loads `synthetic-case.json` and renders it with the same `buildReport()` and `render.mjs` the tests use, escaping every case-supplied string. Edit the JSON and reload to see the report change. Browsers block module and JSON loading over `file://`, which is why `serve.mjs` exists. It is a Node standard-library server bound to 127.0.0.1, read-only, serves a fixed file allowlist, and sets a strict CSP. Timestamps must include `Z` or a `±hh:mm` offset.
