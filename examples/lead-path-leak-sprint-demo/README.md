# Lead-Path Revenue Leak Evidence Sprint — white-label demo

All data in this directory is **synthetic**: fictional agency, client, lead and `*.example` domains. No network, no dependencies.

## What the sprint checks
1. Did the first outbound human contact (call, sms or email) reach a lead within the SLA after CRM lead creation?
2. Do the supplied contact logs actually cover every in-scope channel and the full time interval, so "no earlier contact" is supported rather than merely unobserved?
3. An illustrative gross-margin-at-risk figure from agency-supplied assumptions.

## What the agency provides
CRM export, intake log, contact logs with a coverage statement (channels and window), the SLA definition, and risk assumptions.

## What the agency gets
An evidence-cited report: every finding references record IDs (EV-...), with a white-label slot for your agency name.

## What it can and cannot establish
Can: timing versus SLA, and whether log coverage supports "no earlier contact". Cannot: realized loss, causal attribution, recovered revenue, or any guarantee. The dollar figure is an ILLUSTRATIVE ESTIMATE built from assumptions, not measurements. If coverage is incomplete the report says "no earlier contact" cannot be confirmed, sets `verdict: "UNCONFIRMED_COVERAGE_GAP"` and `breachConfirmed: false`, and marks the risk estimate as not applicable to the lead (`risk.appliesToThisLead: false`).

## Reproduce
```
node examples/lead-path-leak-sprint-demo/sprint.mjs
node --test examples/lead-path-leak-sprint-demo/sprint.test.mjs
```
Open `demo.html` in a browser for the sample report.
