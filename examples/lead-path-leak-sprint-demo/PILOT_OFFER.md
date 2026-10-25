# Agency Pilot: Lead-Path Revenue Leak Evidence Sprint

> Draft offer for a white-label agency pilot. The example in this directory uses **synthetic data only**. There are no customers, results or testimonials behind this document.

## Agency inputs
- CRM export for the pilot window: lead ID, created and assigned timestamps (with time zone), assignee.
- Intake/form log: submission ID and timestamp.
- Outbound contact logs for every channel in scope (call, SMS, email): lead ID, channel, direction, human vs automated, timestamp.
- A written coverage statement: which channels and which time window the logs completely cover.
- The SLA to test (for example "first human outbound attempt within 15 minutes").
- Optional, for an illustrative estimate: average ticket, baseline conversion, gross margin, and an assumed share of conversion kept after a late response. These are the agency's own assumptions.

## What is actually checked
**Deterministic checks (code, reproducible, same input gives the same output):**
- Elapsed time from CRM lead creation to the first qualifying outbound contact for that lead, compared against the SLA. Exactly at the SLA counts as within it.
- Contacts belonging to other leads are ignored. Timestamps without an explicit time zone are rejected.
- Whether the *declared* coverage spans every in-scope channel and the full interval. If not, the verdict is `UNCONFIRMED_COVERAGE_GAP`.
- The illustrative estimate formula, shown only for a `CONFIRMED_BREACH`.

**Human / source reconciliation (separate, performed only if agreed and recorded):**
- Checking a sample of the supplied logs against an authoritative source the agency identifies, such as the phone system's native call report or the email provider's sent log, to test the coverage declaration.
- Results go into a reconciliation record (who, when, and the evidence IDs reconciled against). Without that record, every report states **Independent reconciliation: NOT PERFORMED** and the coverage class stays `SUPPLIER_DECLARED_COMPLETE`.

## Evidence delivered
- Per-lead report (HTML and JSON): verdict, confirmation basis, cited evidence IDs and timestamps, SLA math, coverage class, reconciliation status.
- An estimate, only where the breach is confirmed, with every assumption and the formula visible and labelled *ILLUSTRATIVE ESTIMATE: not realized loss, not causal attribution, not recovered revenue, not a promise*.
- The exact inputs and the version of the check code, so the agency can rerun the report themselves.

## Objective acceptance criteria
The pilot is accepted when all of these hold:
1. Every lead in the agreed sample has a report with one of the defined verdicts.
2. Every timing finding cites the evidence IDs it uses, and rerunning on the same inputs reproduces it exactly.
3. No report claims "no earlier contact" where coverage is incomplete, and no report claims independent reconciliation without a reconciliation record.
4. No lead-specific estimate appears unless the verdict is `CONFIRMED_BREACH`.
5. The agency can spot-check at least 5 findings against its own systems and confirm the cited records match.

## Limitations
- It measures timing against the records supplied. It cannot see contacts that were never logged.
- A supplier-declared coverage statement is taken as declared unless reconciliation is performed.
- It does not establish lost revenue, that a delay caused a lost sale, recovered revenue, or future results. Estimates are only as good as the agency's assumptions.
- It is not legal, compliance or financial advice.

## Proposed data handling
- Minimum fields only. No message bodies or call recordings. Pseudonymous lead IDs are preferred, and contact details are not needed.
- Processed locally or in the agency's own environment. Not shared with third parties. Leads are never contacted.
- Inputs and working copies are deleted within 30 days of acceptance, or sooner on request. The agency keeps the reports.

## Pilot price hypothesis (UNVALIDATED)
**Hypothesis only, not a quote and not validated with any buyer:** a fixed fee of about **$1,500** for up to 3 client accounts and a 30-day lead window, with independent reconciliation priced separately if requested. Price, scope and demand all remain untested.
