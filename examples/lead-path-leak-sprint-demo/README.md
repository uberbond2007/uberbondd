# Lead-Path Revenue Leak Evidence Sprint: white-label demo

All data in this directory is **synthetic**: a fictional agency, client and lead, with `*.example` domains only. There are no dependencies and no external network calls. See [`PILOT_OFFER.md`](PILOT_OFFER.md) for the draft agency pilot.

## What the sprint checks
1. Whether the first outbound human contact (call, SMS or email) reached the lead within the SLA after CRM lead creation.
2. Whether contact-log coverage supports "no earlier contact". Coverage requires the in-scope channels and the full time window to be covered, **plus** an attestation: either a supplier declaration or an independently accepted reconciliation. There are three coverage classes:
   - `SUPPLIER_DECLARED_COMPLETE`: the channels and window are covered *and* `coverage.declaration` is a valid record with an evidence ID, a declarant, a timestamp with a zone, and a statement. The report shows the declaration and its evidence ID. This is the supplier's own assertion, not independent verification. **The sample is in this class (declaration `EV-DEC-001`). Independent reconciliation was NOT PERFORMED (status `NOT_RECORDED`).**
   - `INDEPENDENTLY_RECONCILED_COMPLETE`: the channels and window are covered *and* the reconciliation is `INDEPENDENTLY_ACCEPTED` (below). Naming a reconciler, a time and typed evidence IDs is **not** enough.
   - `INCOMPLETE_OR_MISSING`: a channel or part of the time window is not covered, or there is neither a valid declaration record nor an `INDEPENDENTLY_ACCEPTED` reconciliation. A reconciliation that is only `RECORDED_UNVERIFIED` does not count, and the `basis` label alone never counts. The verdict is `UNCONFIRMED_COVERAGE_GAP`.

   **Reconciliation status** is reported separately from the coverage class, and the report shows the references and review state:
   | Status | Meaning |
   |---|---|
   | `NOT_RECORDED` | No reconciliation object was supplied. The report says "Independent reconciliation: NOT PERFORMED". |
   | `RECORDED_UNVERIFIED` | A reconciliation object was supplied, but at least one check below failed. It does not establish coverage. |
   | `INDEPENDENTLY_ACCEPTED` | Every check below passed. Only this status can produce `INDEPENDENTLY_RECONCILED_COMPLETE`. |

   To reach `INDEPENDENTLY_ACCEPTED`, all of these must hold:
   - `coverage.reconciliation` has a `reconciliationId`, a `reconciledBy` name, a zoned `reconciledAt`, and a list of `authoritativeSourceEvidenceIds` with no repeats.
   - Each referenced ID resolves to **exactly one** supplied object in `records.authoritativeSources` with a nonempty `id`, `source` and `event` and a zoned `timestamp`. A missing, duplicated or incomplete source record leaves the status `RECORDED_UNVERIFIED`.
   - A separate `coverage.reconciliationReview` record has its own `id` (different from the reconciliation ID), a `reconciliationId` matching the reconciliation, `decision: "ACCEPTED"`, a zoned `reviewedAt` that is not before `reconciledAt`, and a `reviewedBy` name distinct from `reconciledBy`.

   **What the code does not do:** these are presence and link checks only. The software does not authenticate the provenance of any authoritative-source artifact, does not verify that a source is independent of the supplier, and does not authenticate the reviewer's identity. Those remain human judgements.
3. An illustrative gross-margin-at-risk figure from agency-supplied assumptions. It is shown **only** for `CONFIRMED_BREACH`; otherwise `buildReport` returns null amounts and the page shows no amount.

## What the agency provides and gets
The agency provides a CRM export, an intake log, contact logs with a coverage statement, the SLA definition, and optional risk assumptions. It gets a report with the verdict, its basis, the cited evidence IDs and timestamps, the SLA math, the coverage class, and the reconciliation status with its references and review.

## What it can and cannot establish
It can establish timing against the SLA, and whether the stated coverage supports "no earlier contact". It cannot establish realized loss, causal attribution, recovered revenue or any guarantee. A supplier's coverage declaration is an assertion, not proof. Even an `INDEPENDENTLY_ACCEPTED` reconciliation shows only that the supplied records are present and linked and that a distinct reviewer's acceptance is recorded; it does not prove the artifacts are genuine or the reviewer's identity.

## Reproduce
```
node examples/lead-path-leak-sprint-demo/sprint.mjs                  # report as JSON
node --test examples/lead-path-leak-sprint-demo/sprint.test.mjs      # focused tests
node examples/lead-path-leak-sprint-demo/serve.mjs                   # then open 127.0.0.1:8787/demo.html
```
`demo.html` loads `synthetic-case.json` and renders it with the same `buildReport()` and `render.mjs` the tests use, escaping every case-supplied string. Edit the JSON and reload to see the report change. Browsers block module and JSON loading over `file://`, which is why `serve.mjs` exists. It is a Node standard-library server bound to 127.0.0.1, read-only, serves a fixed file allowlist, and sets a strict CSP. Timestamps must include `Z` or a `±hh:mm` offset.
