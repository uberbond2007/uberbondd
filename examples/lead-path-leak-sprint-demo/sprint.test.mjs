import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { evaluateSla, assessContactCoverage, estimateRisk, buildReport } from './sprint.mjs';

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
  const html = readFileSync(path.join(here, 'demo.html'), 'utf8');
  assert.ok(html.includes(LABEL));
  for (const id of ['EV-INT-001', 'EV-CRM-001', 'EV-CRM-002', 'EV-CON-002', 'EV-CON-003']) assert.ok(html.includes(id));
  assert.ok(html.includes('34.43'));
  assert.ok(!html.includes('http://'));
  assert.ok(!html.includes('https://'));
  assert.ok(!html.includes('<script'));
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
