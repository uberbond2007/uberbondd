// Pure, dependency-free core. Safe to import in Node and in the browser (no static node: imports).

export const RISK_LABEL =
  'ILLUSTRATIVE ESTIMATE — not realized loss, not causal attribution, not recovered revenue, not a promise';
export const RISK_FORMULA =
  'averageTicketUsd × baselineConversionProbability × grossMarginRate × (1 − conversionRetainedAfterLateResponse)';

// Timestamps must carry an explicit zone: Date.parse reads zone-less ISO strings as local time,
// which would make SLA minutes depend on the reviewer's machine.
const ZONED_ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$/;
const ms = (iso) => {
  if (typeof iso !== 'string' || !ZONED_ISO.test(iso)) throw new Error(`Timestamp must be ISO 8601 with Z or ±hh:mm: ${iso}`);
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) throw new Error(`Invalid timestamp: ${iso}`);
  return t;
};

function findCreated(caseData, leadId) {
  const lead = caseData.lead;
  if (!lead || lead.id !== leadId) throw new Error(`Lead not found: ${leadId}`);
  const created = (caseData.records?.crm ?? []).find(
    (r) => r.leadId === leadId && r.type === 'lead_created',
  );
  if (!created) throw new Error(`Missing lead-created CRM record for ${leadId}`);
  return created;
}

function firstContact(caseData, leadId, createdMs) {
  const scope = caseData.coverage.channelsInScope;
  return (caseData.records.contacts ?? [])
    .filter(
      (c) =>
        c.leadId === leadId &&
        c.direction === 'outbound' &&
        c.actor === 'human' &&
        scope.includes(c.channel) &&
        ms(c.timestamp) >= createdMs,
    )
    .sort((a, b) => ms(a.timestamp) - ms(b.timestamp))[0];
}

export function evaluateSla(caseData, leadId) {
  const created = findCreated(caseData, leadId);
  const createdMs = ms(created.timestamp);
  const slaMinutes = caseData.sla.firstResponseMinutes;
  const assignment = (caseData.records.crm ?? []).find(
    (r) => r.leadId === leadId && r.type === 'lead_assigned',
  );
  const contact = firstContact(caseData, leadId, createdMs);
  const evidenceIds = [created.id];
  if (assignment) evidenceIds.push(assignment.id);
  if (!contact) {
    return {
      leadId,
      createdAt: created.timestamp,
      firstContactAt: null,
      firstContactChannel: null,
      elapsedMinutes: null,
      slaMinutes,
      breachMinutes: 0,
      status: 'NO_CONTACT_FOUND',
      evidenceIds,
    };
  }
  evidenceIds.push(contact.id);
  const elapsedMinutes = (ms(contact.timestamp) - createdMs) / 60000;
  return {
    leadId,
    createdAt: created.timestamp,
    firstContactAt: contact.timestamp,
    firstContactChannel: contact.channel,
    elapsedMinutes,
    slaMinutes,
    breachMinutes: Math.max(0, elapsedMinutes - slaMinutes),
    status: elapsedMinutes <= slaMinutes ? 'WITHIN_SLA' : 'BREACH',
    evidenceIds,
  };
}

const nonEmpty = (v) => typeof v === 'string' && v.trim() !== '';
const validInstant = (v) => typeof v === 'string' && ZONED_ISO.test(v) && Number.isFinite(Date.parse(v));

export const RECONCILIATION_STATUS = Object.freeze({
  NOT_RECORDED: 'NOT_RECORDED',
  RECORDED_UNVERIFIED: 'RECORDED_UNVERIFIED',
  INDEPENDENTLY_ACCEPTED: 'INDEPENDENTLY_ACCEPTED',
});
export const AUTHENTICATION_CAVEAT =
  'Presence and link checks are deterministic validation only. This software does not authenticate provider artifacts or reviewer identity.';

const str = (v) => (typeof v === 'string' ? v : null);
const isRecord = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);
const sameName = (a, b) => a.trim().toLowerCase() === b.trim().toLowerCase();

// Resolve one referenced ID to exactly one supplied authoritative-source object. A typed ID alone proves nothing.
function resolveReference(caseData, id) {
  if (!nonEmpty(id)) return { id: str(id) ?? '(not a string)', state: 'INVALID', problem: 'reference is not a nonempty string' };
  const sources = Array.isArray(caseData.records?.authoritativeSources) ? caseData.records.authoritativeSources : [];
  const hits = sources.filter((x) => isRecord(x) && x.id === id);
  if (hits.length === 0) return { id, state: 'MISSING', problem: `${id} does not resolve to any object in records.authoritativeSources` };
  if (hits.length > 1) return { id, state: 'AMBIGUOUS', problem: `${id} resolves to ${hits.length} objects; it must resolve to exactly one` };
  const h = hits[0];
  if (!nonEmpty(h.source) || !nonEmpty(h.event) || !validInstant(h.timestamp)) {
    return { id, state: 'INVALID', problem: `${id} is missing a nonempty source or event, or a zoned timestamp` };
  }
  return { id, state: 'RESOLVED', source: h.source, event: h.event, timestamp: h.timestamp };
}

// Reconciliation status is a deterministic structural check, never authentication:
//  - NOT_RECORDED: no reconciliation object was supplied.
//  - RECORDED_UNVERIFIED: an object was supplied but a link, field or review check failed.
//  - INDEPENDENTLY_ACCEPTED: record fields valid, every referenced ID resolves uniquely to a supplied
//    authoritative-source object, and a separate review record accepts it with a distinct reviewer.
// A coverage.basis label is ignored as proof.
function reconciliationStatus(caseData, cov) {
  const r = cov.reconciliation;
  if (!isRecord(r)) {
    return { status: RECONCILIATION_STATUS.NOT_RECORDED, reconciliation: null, references: [], review: null, problems: [] };
  }
  const problems = [];
  const reconciliation = { reconciliationId: str(r.reconciliationId), reconciledBy: str(r.reconciledBy), reconciledAt: str(r.reconciledAt) };
  if (!nonEmpty(r.reconciliationId)) problems.push('reconciliation has no reconciliationId');
  if (!nonEmpty(r.reconciledBy)) problems.push('reconciliation has no reconciledBy');
  if (!validInstant(r.reconciledAt)) problems.push('reconciliation has no zoned reconciledAt');

  const ids = Array.isArray(r.authoritativeSourceEvidenceIds) ? r.authoritativeSourceEvidenceIds : [];
  if (ids.length === 0) problems.push('reconciliation references no authoritative-source evidence IDs');
  if (new Set(ids).size !== ids.length) problems.push('reconciliation lists the same authoritative-source evidence ID more than once');
  const references = ids.map((id) => resolveReference(caseData, id));
  for (const ref of references) if (ref.problem) problems.push(ref.problem);

  const v = cov.reconciliationReview;
  let review = null;
  if (!isRecord(v)) {
    problems.push('no coverage.reconciliationReview record');
  } else {
    review = { id: str(v.id), reconciliationId: str(v.reconciliationId), reviewedBy: str(v.reviewedBy), reviewedAt: str(v.reviewedAt), decision: str(v.decision), accepted: false };
    const rp = [];
    if (!nonEmpty(v.id)) rp.push('review has no ID');
    else if (v.id === r.reconciliationId) rp.push('review ID must differ from the reconciliation ID');
    if (!nonEmpty(v.reconciliationId) || v.reconciliationId !== r.reconciliationId) rp.push('review reconciliationId does not match the reconciliation record');
    if (v.decision !== 'ACCEPTED') rp.push('review decision is not ACCEPTED');
    if (!validInstant(v.reviewedAt)) rp.push('review has no zoned reviewedAt');
    else if (validInstant(r.reconciledAt) && ms(v.reviewedAt) < ms(r.reconciledAt)) rp.push('review is dated before the reconciliation');
    if (!nonEmpty(v.reviewedBy)) rp.push('review has no reviewer name');
    else if (nonEmpty(r.reconciledBy) && sameName(v.reviewedBy, r.reconciledBy)) rp.push('reviewer is not distinct from the reconciler');
    problems.push(...rp);
    review.accepted = rp.length === 0;
  }

  const accepted = problems.length === 0;
  return {
    status: accepted ? RECONCILIATION_STATUS.INDEPENDENTLY_ACCEPTED : RECONCILIATION_STATUS.RECORDED_UNVERIFIED,
    reconciliation,
    references,
    review,
    problems,
  };
}

// A supplier declaration counts only as an explicit record: evidence ID, declarant, zoned timestamp, statement.
// The channel/window arrays alone are claims about coverage, not a declaration of it.
function declarationStatus(cov) {
  const d = cov.declaration;
  const valid = !!d && nonEmpty(d.evidenceId) && nonEmpty(d.declaredBy) && validInstant(d.declaredAt) && nonEmpty(d.statement);
  return valid
    ? { valid, record: { evidenceId: d.evidenceId, declaredBy: d.declaredBy, declaredAt: d.declaredAt, statement: d.statement } }
    : { valid, record: null };
}

export function assessContactCoverage(caseData, leadId, untilIso) {
  const created = findCreated(caseData, leadId);
  const cov = caseData.coverage;
  const missingChannels = cov.channelsInScope.filter((c) => !cov.channelsCovered.includes(c));
  const windowCovered =
    ms(cov.windowStart) <= ms(created.timestamp) && ms(cov.windowEnd) >= ms(untilIso);
  const reconciliation = reconciliationStatus(caseData, cov);
  const declaration = declarationStatus(cov);
  const independent = reconciliation.status === RECONCILIATION_STATUS.INDEPENDENTLY_ACCEPTED;
  const attested = independent || declaration.valid;
  const supported = missingChannels.length === 0 && windowCovered && attested;
  let coverageClass = 'INCOMPLETE_OR_MISSING';
  if (supported) coverageClass = independent ? 'INDEPENDENTLY_RECONCILED_COMPLETE' : 'SUPPLIER_DECLARED_COMPLETE';
  const reasons = [];
  if (missingChannels.length) reasons.push(`channels not covered by logs: ${missingChannels.join(', ')}`);
  if (!windowCovered) reasons.push('log window does not cover [lead created, until]');
  if (!attested) reasons.push('no valid supplier declaration record and no independently accepted reconciliation');
  if (reconciliation.status === RECONCILIATION_STATUS.RECORDED_UNVERIFIED) {
    reasons.push(`reconciliation is RECORDED_UNVERIFIED (${reconciliation.problems.join('; ')})`);
  }
  if (cov.basis === 'INDEPENDENTLY_RECONCILED' && !independent) {
    reasons.push('basis label claims independent reconciliation, but labels are not proof and the status is ' + reconciliation.status);
  }
  let reason;
  if (!supported) {
    reason = `Coverage gap (${reasons.join('; ')}). Absence of evidence is not evidence of no contact.`;
  } else if (independent) {
    reason = 'All in-scope channels are covered, the log window spans the interval, and a reconciliation record linked to supplied authoritative-source records has an accepting review by a distinct reviewer. ' + AUTHENTICATION_CAVEAT;
  } else {
    const recon = reconciliation.status === RECONCILIATION_STATUS.NOT_RECORDED
      ? 'Independent reconciliation was NOT PERFORMED.'
      : `A reconciliation record was supplied but is RECORDED_UNVERIFIED (${reconciliation.problems.join('; ')}), so independent reconciliation is not established.`;
    reason = `Supplier declaration ${declaration.record.evidenceId} states all in-scope channels are covered for a window spanning the interval; absence of earlier outbound contact is supported only by the logs as supplied. ${recon}`;
  }
  return {
    conclusion: supported ? 'NO_EARLIER_CONTACT_SUPPORTED' : 'INCONCLUSIVE_COVERAGE_GAP',
    coverageClass,
    reconciliationStatus: reconciliation.status,
    reconciliation: reconciliation.reconciliation,
    reconciliationReferences: reconciliation.references,
    reconciliationReview: reconciliation.review,
    reconciliationProblems: reconciliation.problems,
    authenticationCaveat: AUTHENTICATION_CAVEAT,
    declaredBasisLabel: cov.basis ?? null,
    declaration: declaration.record,
    missingChannels,
    windowCovered,
    reason,
  };
}

export function estimateRisk(assumptions) {
  const a = assumptions ?? {};
  const names = [
    'averageTicketUsd',
    'baselineConversionProbability',
    'grossMarginRate',
    'conversionRetainedAfterLateResponse',
  ];
  for (const n of names) {
    if (typeof a[n] !== 'number' || !Number.isFinite(a[n])) throw new Error(`${n} must be a finite number`);
  }
  if (a.averageTicketUsd < 0) throw new Error('averageTicketUsd must be >= 0');
  for (const n of names.slice(1)) {
    if (a[n] < 0 || a[n] > 1) throw new Error(`${n} must be within [0, 1]`);
  }
  const timely = a.averageTicketUsd * a.baselineConversionProbability * a.grossMarginRate;
  const atRisk = timely * (1 - a.conversionRetainedAfterLateResponse);
  const cents = (x) => Math.round(x * 100 + 1e-6) / 100;
  return {
    inputs: { ...a },
    formula: RISK_FORMULA,
    expectedGrossMarginIfTimelyUsd: cents(timely),
    illustrativeAtRiskGrossMarginUsd: cents(atRisk),
    label: RISK_LABEL,
    claimFlags: { realizedLoss: false, causalAttribution: false, recoveredRevenue: false, guarantee: false },
  };
}

export function buildReport(caseData, leadId) {
  const sla = evaluateSla(caseData, leadId);
  const until = sla.firstContactAt ?? caseData.coverage.windowEnd;
  const coverage = assessContactCoverage(caseData, leadId, until);
  const assumptions = Object.fromEntries(
    Object.entries(caseData.riskAssumptions).map(([k, v]) => [k, v.value]),
  );
  const risk = estimateRisk(assumptions);
  const supported = coverage.conclusion === 'NO_EARLIER_CONTACT_SUPPORTED';
  let summary;
  if (sla.status === 'NO_CONTACT_FOUND') {
    summary = 'No qualifying outbound contact was found in the provided records.';
  } else {
    summary = `First qualifying outbound contact came ${sla.elapsedMinutes} min after lead creation (SLA ${sla.slaMinutes} min): ${sla.status}${sla.breachMinutes ? `, ${sla.breachMinutes} min over` : ''}.`;
  }
  if (!supported) {
    summary += ' Because contact-log coverage is incomplete, "no earlier contact" cannot be confirmed.';
  } else if (coverage.coverageClass === 'INDEPENDENTLY_RECONCILED_COMPLETE') {
    summary += ' An accepted reconciliation record supports that no earlier contact occurred (presence and links checked only; provider artifacts and reviewer identity are not authenticated).';
  } else if (coverage.reconciliationStatus === RECONCILIATION_STATUS.NOT_RECORDED) {
    summary += ' The supplier-declared logs support that no earlier contact occurred; independent reconciliation was NOT PERFORMED.';
  } else {
    summary += ' The supplier-declared logs support that no earlier contact occurred; a reconciliation record was supplied but is RECORDED_UNVERIFIED, so independent reconciliation is not established.';
  }
  // A breach is only confirmed when the logs could have shown an earlier contact and did not.
  const confirmationBasis = !supported ? null : coverage.coverageClass;
  let verdict;
  if (!supported) verdict = 'UNCONFIRMED_COVERAGE_GAP';
  else if (sla.status === 'BREACH') verdict = 'CONFIRMED_BREACH';
  else if (sla.status === 'WITHIN_SLA') verdict = 'WITHIN_SLA';
  else verdict = 'NO_CONTACT_IN_COVERED_LOGS';
  const breachConfirmed = verdict === 'CONFIRMED_BREACH';
  return {
    synthetic: caseData.synthetic === true,
    leadId,
    verdict,
    breachConfirmed,
    confirmationBasis,
    reconciliationStatus: coverage.reconciliationStatus,
    summary,
    sla,
    coverage,
    risk: breachConfirmed
      ? { ...risk, appliesToThisLead: true }
      : {
          appliesToThisLead: false,
          label: risk.label,
          formula: risk.formula,
          expectedGrossMarginIfTimelyUsd: null,
          illustrativeAtRiskGrossMarginUsd: null,
          suppressedReason: `No lead-specific estimate: verdict is ${verdict}, not CONFIRMED_BREACH.`,
          claimFlags: risk.claimFlags,
        },
  };
}

// CLI: `node sprint.mjs` prints the report for synthetic-case.json. Skipped in the browser.
if (typeof process !== 'undefined' && process.argv?.[1]) {
  const { fileURLToPath } = await import('node:url');
  const path = await import('node:path');
  if (path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
    const { readFileSync } = await import('node:fs');
    const file = path.join(path.dirname(fileURLToPath(import.meta.url)), 'synthetic-case.json');
    const data = JSON.parse(readFileSync(file, 'utf8'));
    console.log(JSON.stringify(buildReport(data, data.lead.id), null, 2));
  }
}
