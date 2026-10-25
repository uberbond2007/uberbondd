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
  assert.equal(r.independentReconciliation, 'NOT_PERFORMED');
  const html = renderReport(base, r);
  assert.match(html, /Independent reconciliation: <strong>NOT PERFORMED<\/strong>/);
  assert.ok(!html.includes('INDEPENDENTLY_RECONCILED') && !html.includes('PERFORMED</strong> against'));
  // A claimed basis without a reconciliation record never upgrades to independent.
  const c = structuredClone(base);
  c.coverage.basis = 'INDEPENDENTLY_RECONCILED';
  c.coverage.reconciliation = { reconciledBy: 'Analyst (synthetic)', reconciledAt: '2026-10-16T10:00:00Z', authoritativeSourceEvidenceIds: [] };
  assert.equal(buildReport(c, LEAD).independentReconciliation, 'NOT_PERFORMED');
  c.coverage.reconciliation.authoritativeSourceEvidenceIds = ['EV-SRC-001'];
  const rec = buildReport(c, LEAD);
  assert.equal(rec.independentReconciliation, 'PERFORMED');
  assert.equal(rec.confirmationBasis, 'INDEPENDENTLY_RECONCILED_COMPLETE');
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
  const html = renderReport(c, buildReport(c, LEAD));
  assert.ok(!/<script/i.test(html));
  assert.ok(!/<img/i.test(html));
  assert.ok(!html.includes('<b>x</b>'));
  assert.ok(!/onerror="/i.test(html));
  assert.ok(html.includes('&lt;script&gt;alert(1)&lt;/script&gt;'));
});
