import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { evaluateSla, assessContactCoverage, estimateRisk, buildReport } from './sprint.mjs';
import { renderReport } from './render.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const base = JSON.parse(readFileSync(path.join(here, 'synthetic-case.json'), 'utf8'));
const LEAD = 'LEAD-1001';
const LABEL = 'ILLUSTRATIVE ESTIMATE — not realized loss, not causal attribution, not recovered revenue, not a promise';
// A fully linked synthetic reconciliation: record, one supplied authoritative-source object, and a distinct reviewer's acceptance.
const acceptedCase = () => {
  const c = structuredClone(base);
  c.records.authoritativeSources = [
    { id: 'EV-SRC-001', source: 'Synthetic phone-system call report', event: 'Outbound call list export for 2026-10-14', timestamp: '2026-10-15T08:00:00Z' },
  ];
  c.coverage.reconciliation = {
    reconciliationId: 'REC-001', reconciledBy: 'Analyst A (synthetic)', reconciledAt: '2026-10-16T10:00:00Z',
    authoritativeSourceEvidenceIds: ['EV-SRC-001'],
  };
  c.coverage.reconciliationReview = {
    id: 'REV-001', reconciliationId: 'REC-001', reviewedBy: 'Reviewer B (synthetic)', reviewedAt: '2026-10-16T12:00:00Z', decision: 'ACCEPTED',
  };
  return c;
};
const assumptions = () =>
  Object.fromEntries(Object.entries(base.riskAssumptions).map(([k, v]) => [k, v.value]));

test('SLA breach math and evidence ids', () => {
  const r = evaluateSla(base, LEAD);
  assert.equal(r.elapsedMinutes, 47);
  assert.equal(r.breachMinutes, 32);
  assert.equal(r.status, 'BREACH');
  for (const id of ['EV-CRM-001', 'EV-CRM-002', 'EV-CON-002']) assert.ok(r.evidenceIds.includes(id));
  assert.ok(!r.evidenceIds.includes('EV-CON-001'));
});

test('exactly 15 minutes is WITHIN_SLA', () => {
  const c = structuredClone(base);
  c.records.contacts.find((x) => x.id === 'EV-CON-002').timestamp = '2026-10-14T14:17:00Z';
  const r = evaluateSla(c, LEAD);
  assert.equal(r.elapsedMinutes, 15);
  assert.equal(r.breachMinutes, 0);
  assert.equal(r.status, 'WITHIN_SLA');
});

test('no contact found', () => {
  const c = structuredClone(base);
  c.records.contacts = c.records.contacts.filter((x) => x.leadId !== LEAD);
  assert.equal(evaluateSla(c, LEAD).status, 'NO_CONTACT_FOUND');
});

test('throws on missing lead or created record', () => {
  assert.throws(() => evaluateSla(base, 'LEAD-NOPE'));
  const c = structuredClone(base);
  c.records.crm = c.records.crm.filter((x) => x.type !== 'lead_created');
  assert.throws(() => evaluateSla(c, LEAD));
});

test('full coverage supports no earlier contact', () => {
  const r = assessContactCoverage(base, LEAD, '2026-10-14T14:49:00Z');
  assert.equal(r.conclusion, 'NO_EARLIER_CONTACT_SUPPORTED');
  assert.equal(r.windowCovered, true);
  assert.deepEqual(r.missingChannels, []);
});

test('missing sms coverage is inconclusive', () => {
  const c = structuredClone(base);
  c.coverage.channelsCovered = ['call', 'email'];
  const r = assessContactCoverage(c, LEAD, '2026-10-14T14:49:00Z');
  assert.equal(r.conclusion, 'INCONCLUSIVE_COVERAGE_GAP');
  assert.deepEqual(r.missingChannels, ['sms']);
  assert.match(buildReport(c, LEAD).summary, /cannot be confirmed/);
});

test('report confirms breach only when coverage supports it', () => {
  const full = buildReport(base, LEAD);
  assert.equal(full.verdict, 'CONFIRMED_BREACH');
  assert.equal(full.breachConfirmed, true);
  assert.equal(full.risk.appliesToThisLead, true);
  const c = structuredClone(base);
  c.coverage.channelsCovered = ['call', 'email'];
  const gap = buildReport(c, LEAD);
  assert.equal(gap.sla.status, 'BREACH');
  assert.equal(gap.verdict, 'UNCONFIRMED_COVERAGE_GAP');
  assert.equal(gap.breachConfirmed, false);
  assert.equal(gap.risk.appliesToThisLead, false);
});

test('window ending before contact is inconclusive', () => {
  const c = structuredClone(base);
  c.coverage.windowEnd = '2026-10-14T14:30:00Z';
  const r = assessContactCoverage(c, LEAD, '2026-10-14T14:49:00Z');
  assert.equal(r.windowCovered, false);
  assert.equal(r.conclusion, 'INCONCLUSIVE_COVERAGE_GAP');
});

test('risk math, label and flags', () => {
  const r = estimateRisk(assumptions());
  assert.equal(r.illustrativeAtRiskGrossMarginUsd, 34.43);
  assert.equal(r.expectedGrossMarginIfTimelyUsd, 114.75);
  assert.ok(r.label.includes('not realized loss'));
  assert.equal(r.label, LABEL);
  assert.deepEqual(r.claimFlags, { realizedLoss: false, causalAttribution: false, recoveredRevenue: false, guarantee: false });
});

test('invalid assumptions throw', () => {
  assert.throws(() => estimateRisk({ ...assumptions(), baselineConversionProbability: 1.2 }));
  assert.throws(() => estimateRisk({ ...assumptions(), averageTicketUsd: -1 }));
  assert.throws(() => estimateRisk({ ...assumptions(), grossMarginRate: NaN }));
});

test('demo.html matches report and is self-contained', () => {
  // Adapted: demo.html now renders buildReport() via local modules, so content is checked on the rendered output.
  const html = readFileSync(path.join(here, 'demo.html'), 'utf8');
  const rendered = renderReport(base, buildReport(base, LEAD));
  assert.ok(rendered.includes(LABEL));
  for (const id of ['EV-INT-001', 'EV-CRM-001', 'EV-CRM-002', 'EV-CON-002', 'EV-CON-003']) assert.ok(rendered.includes(id));
  assert.ok(rendered.includes('34.43'));
  assert.ok(html.includes('SYNTHETIC DEMO DATA') && rendered.includes('SYNTHETIC DEMO DATA'));
  assert.ok(!html.includes('http://'));
  assert.ok(!html.includes('https://'));
  assert.deepEqual(html.match(/<script\b[^>]*>/g), ['<script type="module" src="./demo.mjs">']);
});

test('synthetic-case.json is synthetic with .example domains only', () => {
  assert.equal(base.synthetic, true);
  const strings = [];
  (function walk(v) {
    if (typeof v === 'string') strings.push(v);
    else if (v && typeof v === 'object') Object.values(v).forEach(walk);
  })(base);
  const emails = strings.flatMap((s) => s.match(/[\w.+-]+@[\w.-]+/g) ?? []);
  assert.ok(emails.length > 0);
  for (const e of emails) assert.ok(e.endsWith('.example'), e);
  const domains = [base.agency.domain, base.client.domain];
  for (const d of domains) assert.ok(d.endsWith('.example'), d);
  for (const s of strings) {
    for (const h of s.match(/\b[a-z0-9-]+(\.[a-z0-9-]+)+\b/gi) ?? []) {
      if (/^\d/.test(h) || /\.(json|mjs|html)$/.test(h)) continue;
      if (/^[A-Z]/.test(h)) continue;
      assert.ok(h.endsWith('.example'), `non-example host: ${h}`);
    }
  }
});

// --- Decisive product-readiness cases ---

test('decisive: 47-minute supplied contact vs 15-minute SLA, with evidence IDs and supplier-declared basis', () => {
  const r = buildReport(base, LEAD);
  assert.equal(r.sla.elapsedMinutes, 47);
  assert.equal(r.sla.breachMinutes, 32);
  assert.equal(r.verdict, 'CONFIRMED_BREACH');
  assert.deepEqual(r.sla.evidenceIds, ['EV-CRM-001', 'EV-CRM-002', 'EV-CON-002']);
  assert.equal(r.confirmationBasis, 'SUPPLIER_DECLARED_COMPLETE');
  const html = renderReport(base, r);
  assert.match(html, /Independent reconciliation: <strong>NOT PERFORMED<\/strong>/);
  assert.equal(r.coverage.declaration.evidenceId, 'EV-DEC-001');
  assert.ok(html.includes('Supplier declaration <strong>EV-DEC-001</strong>'));
  assert.ok(html.includes('Operations lead, Northwind Growth Partners (synthetic)'));
  assert.ok(!html.includes('INDEPENDENTLY_RECONCILED') && !html.includes('PERFORMED</strong> against'));
  // A basis label never upgrades coverage, and the sample records no reconciliation at all.
  assert.equal(r.reconciliationStatus, 'NOT_RECORDED');
  assert.equal(r.coverage.reconciliationStatus, 'NOT_RECORDED');
  const labelled = structuredClone(base);
  labelled.coverage.basis = 'INDEPENDENTLY_RECONCILED';
  assert.equal(buildReport(labelled, LEAD).confirmationBasis, 'SUPPLIER_DECLARED_COMPLETE');
  // Only a linked, reviewed reconciliation reaches INDEPENDENTLY_ACCEPTED, and it stands without a declaration.
  const ok = acceptedCase();
  const rec = buildReport(ok, LEAD);
  assert.equal(rec.reconciliationStatus, 'INDEPENDENTLY_ACCEPTED');
  assert.equal(rec.confirmationBasis, 'INDEPENDENTLY_RECONCILED_COMPLETE');
  ok.coverage.declaration = null;
  assert.equal(buildReport(ok, LEAD).confirmationBasis, 'INDEPENDENTLY_RECONCILED_COMPLETE');
  const page = renderReport(ok, buildReport(ok, LEAD));
  assert.match(page, /INDEPENDENTLY_ACCEPTED/);
  assert.match(page, /EV-SRC-001: source record present: Synthetic phone-system call report/);
  assert.match(page, /does not authenticate provider artifacts or reviewer identity/);
});

test('negative: fabricated reconciliation metadata and typed IDs never yield independent coverage', () => {
  const c = structuredClone(base);
  c.coverage.basis = 'INDEPENDENTLY_RECONCILED';
  c.coverage.reconciliation = {
    reconciliationId: 'REC-FAKE', reconciledBy: 'Analyst A (synthetic)', reconciledAt: '2026-10-16T10:00:00Z',
    authoritativeSourceEvidenceIds: ['EV-SRC-001', 'EV-SRC-002'],
  };
  // Metadata and typed IDs only: no source objects, no review record.
  let r = buildReport(c, LEAD);
  assert.equal(r.reconciliationStatus, 'RECORDED_UNVERIFIED');
  assert.equal(r.confirmationBasis, 'SUPPLIER_DECLARED_COMPLETE');
  assert.deepEqual(r.coverage.reconciliationReferences.map((x) => x.state), ['MISSING', 'MISSING']);
  let html = renderReport(c, r);
  assert.match(html, /<strong>RECORDED_UNVERIFIED<\/strong>/);
  assert.match(html, /source record MISSING/);
  assert.match(html, /No reconciliation review record/);
  assert.match(html, /does not authenticate provider artifacts or reviewer identity/);
  assert.ok(!html.includes('INDEPENDENTLY_ACCEPTED') && !html.includes('INDEPENDENTLY_RECONCILED_COMPLETE'));
  assert.ok(!html.includes('NOT PERFORMED'), 'a supplied record is described as unverified, not as absent');
  // With no valid supplier declaration either, coverage is unconfirmed and the amounts are suppressed.
  c.coverage.declaration = null;
  r = buildReport(c, LEAD);
  assert.equal(r.verdict, 'UNCONFIRMED_COVERAGE_GAP');
  assert.equal(r.coverage.coverageClass, 'INCOMPLETE_OR_MISSING');
  assert.equal(r.risk.illustrativeAtRiskGrossMarginUsd, null);
  assert.ok(!/\$\d/.test(renderReport(c, r)));
});

test('negative: an acceptance record without authoritative records is not independent acceptance', () => {
  const c = acceptedCase();
  delete c.records.authoritativeSources;
  c.coverage.declaration = null;
  let r = buildReport(c, LEAD);
  assert.equal(r.reconciliationStatus, 'RECORDED_UNVERIFIED');
  assert.equal(r.coverage.reconciliationReview.accepted, true, 'the review record itself is well-formed');
  assert.equal(r.verdict, 'UNCONFIRMED_COVERAGE_GAP');
  assert.equal(r.risk.appliesToThisLead, false);
  const html = renderReport(c, r);
  assert.match(html, /EV-SRC-001: <strong>source record MISSING<\/strong>/);
  assert.match(html, /RECORDED_UNVERIFIED/);
  assert.ok(!html.includes('INDEPENDENTLY_ACCEPTED'));
  // Ambiguous or incomplete source objects do not resolve either.
  const dupe = acceptedCase();
  dupe.records.authoritativeSources.push(structuredClone(dupe.records.authoritativeSources[0]));
  assert.deepEqual(buildReport(dupe, LEAD).coverage.reconciliationReferences.map((x) => x.state), ['AMBIGUOUS']);
  const zoneless = acceptedCase();
  zoneless.records.authoritativeSources[0].timestamp = '2026-10-15T08:00:00';
  assert.deepEqual(buildReport(zoneless, LEAD).coverage.reconciliationReferences.map((x) => x.state), ['INVALID']);
  const blank = acceptedCase();
  blank.records.authoritativeSources[0].event = ' ';
  assert.equal(buildReport(blank, LEAD).reconciliationStatus, 'RECORDED_UNVERIFIED');
  // Duplicate reference IDs and a declaration-only ID cannot stand in for a source record.
  const twice = acceptedCase();
  twice.coverage.reconciliation.authoritativeSourceEvidenceIds = ['EV-SRC-001', 'EV-SRC-001'];
  assert.equal(buildReport(twice, LEAD).reconciliationStatus, 'RECORDED_UNVERIFIED');
  const decl = acceptedCase();
  decl.coverage.reconciliation.authoritativeSourceEvidenceIds = ['EV-DEC-001'];
  assert.equal(buildReport(decl, LEAD).coverage.reconciliationReferences[0].state, 'MISSING');
});

test('negative: review defects keep reconciliation unverified', () => {
  const defects = {
    mismatchedReconciliationId: (c) => { c.coverage.reconciliationReview.reconciliationId = 'REC-OTHER'; },
    notAccepted: (c) => { c.coverage.reconciliationReview.decision = 'REJECTED'; },
    reviewedBeforeReconciled: (c) => { c.coverage.reconciliationReview.reviewedAt = '2026-10-16T09:59:00Z'; },
    zonelessReviewTime: (c) => { c.coverage.reconciliationReview.reviewedAt = '2026-10-16T12:00:00'; },
    sameNameAsReconciler: (c) => { c.coverage.reconciliationReview.reviewedBy = '  analyst a (SYNTHETIC) '; },
    reviewIdEqualsReconciliationId: (c) => { c.coverage.reconciliationReview.id = 'REC-001'; },
    noReviewId: (c) => { delete c.coverage.reconciliationReview.id; },
    noReviewRecord: (c) => { delete c.coverage.reconciliationReview; },
    noReconciliationId: (c) => { delete c.coverage.reconciliation.reconciliationId; },
  };
  for (const [name, mutate] of Object.entries(defects)) {
    const c = acceptedCase();
    mutate(c);
    const r = buildReport(c, LEAD);
    assert.equal(r.reconciliationStatus, 'RECORDED_UNVERIFIED', name);
    assert.equal(r.confirmationBasis, 'SUPPLIER_DECLARED_COMPLETE', name);
    assert.match(renderReport(c, r), /RECORDED_UNVERIFIED/, name);
  }
  // A review dated exactly at the reconciliation time is not "before" it.
  const same = acceptedCase();
  same.coverage.reconciliationReview.reviewedAt = same.coverage.reconciliation.reconciledAt;
  assert.equal(buildReport(same, LEAD).reconciliationStatus, 'INDEPENDENTLY_ACCEPTED');
});

test('decisive: changing the contact time updates the rendered report', () => {
  const c = structuredClone(base);
  c.records.contacts.find((x) => x.id === 'EV-CON-002').timestamp = '2026-10-14T14:30:00Z';
  const html = renderReport(c, buildReport(c, LEAD));
  assert.ok(html.includes('2026-10-14T14:30:00Z'));
  assert.ok(html.includes('<td>28 minutes</td>'));
  assert.ok(html.includes('<td>13 minutes</td>'));
  assert.ok(!html.includes('2026-10-14T14:49:00Z'));
  assert.ok(!html.includes('<td>47 minutes</td>'));
  // Zone-less contact times are refused rather than read in the reviewer's local time zone.
  c.records.contacts.find((x) => x.id === 'EV-CON-002').timestamp = '2026-10-14T14:30:00';
  assert.throws(() => buildReport(c, LEAD), /explicit|Z or/);
});

test('decisive: missing SMS coverage prevents confirmation', () => {
  const c = structuredClone(base);
  c.coverage.channelsCovered = ['call', 'email'];
  const r = buildReport(c, LEAD);
  assert.equal(r.sla.status, 'BREACH');
  assert.equal(r.verdict, 'UNCONFIRMED_COVERAGE_GAP');
  assert.equal(r.breachConfirmed, false);
  assert.equal(r.coverage.coverageClass, 'INCOMPLETE_OR_MISSING');
  assert.match(renderReport(c, r), /UNCONFIRMED_COVERAGE_GAP/);
  // Full channel/window arrays without a valid declaration (or reconciliation) record are not complete coverage.
  const variants = {
    missing: (d) => { d.coverage.declaration = null; },
    noEvidenceId: (d) => { d.coverage.declaration.evidenceId = ''; },
    zonelessTime: (d) => { d.coverage.declaration.declaredAt = '2026-10-15T09:00:00'; },
    labelOnly: (d) => { d.coverage.declaration = null; d.coverage.basis = 'INDEPENDENTLY_RECONCILED'; },
  };
  for (const [name, mutate] of Object.entries(variants)) {
    const d = structuredClone(base);
    mutate(d);
    const u = buildReport(d, LEAD);
    assert.equal(u.verdict, 'UNCONFIRMED_COVERAGE_GAP', name);
    assert.equal(u.coverage.coverageClass, 'INCOMPLETE_OR_MISSING', name);
    assert.equal(u.risk.illustrativeAtRiskGrossMarginUsd, null, name);
    const page = renderReport(d, u);
    assert.ok(!/\$\d/.test(page), name);
    assert.ok(page.includes('No valid supplier declaration record'), name);
  }
});

test('decisive: unconfirmed result contains no applicable estimate', () => {
  const c = structuredClone(base);
  c.coverage.channelsCovered = ['call', 'email'];
  const r = buildReport(c, LEAD);
  assert.equal(r.risk.appliesToThisLead, false);
  assert.equal(r.risk.illustrativeAtRiskGrossMarginUsd, null);
  assert.equal(r.risk.expectedGrossMarginIfTimelyUsd, null);
  assert.ok(!JSON.stringify(r).includes('34.43') && !JSON.stringify(r).includes('114.75'));
  const html = renderReport(c, r);
  assert.ok(!/\$\d/.test(html), 'no dollar amount rendered');
  assert.ok(html.includes('No lead-specific estimate shown.'));
});

test('decisive: HTML escaping blocks injected markup and scripts', () => {
  const c = structuredClone(base);
  const evil = '<script>alert(1)</script><img src=x onerror="alert(2)">';
  c.client.name = evil;
  c.records.contacts.find((x) => x.id === 'EV-CON-002').event = evil;
  c.records.crm.find((x) => x.id === 'EV-CRM-002').id = 'EV-CRM-002"><b>x</b>';
  c.sla.definition = evil;
  c.coverage.declaration.statement = evil;
  c.coverage.declaration.declaredBy = evil;
  // Reconciliation, source and review text reaches the page too.
  const rc = acceptedCase();
  c.records.authoritativeSources = rc.records.authoritativeSources;
  c.coverage.reconciliation = rc.coverage.reconciliation;
  c.coverage.reconciliationReview = rc.coverage.reconciliationReview;
  c.records.authoritativeSources[0].source = evil;
  c.records.authoritativeSources[0].event = evil;
  c.coverage.reconciliation.reconciledBy = evil;
  c.coverage.reconciliationReview.reviewedBy = evil + ' reviewer';
  c.coverage.reconciliationReview.decision = evil;
  const html = renderReport(c, buildReport(c, LEAD));
  assert.ok(!/<script/i.test(html));
  assert.ok(!/<img/i.test(html));
  assert.ok(!html.includes('<b>x</b>'));
  assert.ok(!/onerror="/i.test(html));
  assert.ok(html.includes('&lt;script&gt;alert(1)&lt;/script&gt;'));
});
