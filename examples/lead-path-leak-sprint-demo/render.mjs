// Pure HTML renderer for a buildReport() result. Every case-supplied value is passed through esc()
// before insertion; numbers are formatted, never interpolated raw from input strings.

const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;', '`': '&#96;' };
export const esc = (v) => String(v ?? '').replace(/[&<>"'`]/g, (c) => ESC[c]);

const SOURCES = { intake: 'Intake form', crm: 'CRM', contacts: 'Contact log' };
const usd = (n) => `$${Number(n).toFixed(2)}`;
const mins = (n) => `${Number(n)} minutes`;

function timeline(caseData, report) {
  const rows = [];
  for (const [key, label] of Object.entries(SOURCES)) {
    for (const r of caseData.records?.[key] ?? []) rows.push({ ...r, source: label });
  }
  rows.sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
  const cited = new Set(report.sla.evidenceIds);
  return rows
    .map((r) => {
      const note =
        r.leadId && r.leadId !== report.leadId
          ? ' (different lead; ignored)'
          : cited.has(r.id) ? ' (cited)' : '';
      return `<tr><td>${esc(r.id)}</td><td>${esc(r.source)}</td><td>${esc(r.timestamp)}</td><td>${esc(r.event)}${esc(note)}</td></tr>`;
    })
    .join('\n');
}

const REF_TEXT = {
  RESOLVED: (r) => `source record present: ${esc(r.source)}, ${esc(r.event)}, ${esc(r.timestamp)}`,
  MISSING: () => '<strong>source record MISSING</strong> from records.authoritativeSources',
  AMBIGUOUS: () => '<strong>AMBIGUOUS</strong>: resolves to more than one record',
  INVALID: () => '<strong>INVALID</strong>: source record lacks required fields',
};

function reconciliationHtml(c) {
  const st = c.reconciliationStatus;
  const rec = c.reconciliation;
  if (st === 'NOT_RECORDED') {
    return `<p>Independent reconciliation: <strong>NOT PERFORMED</strong> (status <strong>NOT_RECORDED</strong>). No reconciliation record against authoritative-source evidence was supplied${c.declaration ? ', so coverage rests on the supplier declaration only' : ', and no valid supplier declaration exists either, so coverage is not established'}.</p>`;
  }
  const head = st === 'INDEPENDENTLY_ACCEPTED'
    ? 'Independent reconciliation: <strong>INDEPENDENTLY_ACCEPTED</strong> (record, linked source records and an accepting review passed the deterministic checks).'
    : 'Independent reconciliation: <strong>RECORDED_UNVERIFIED</strong>. A record was supplied but it is <strong>not</strong> independently accepted, so it does not establish coverage.';
  const refs = c.reconciliationReferences
    .map((r) => `<li>${esc(r.id)}: ${REF_TEXT[r.state](r)}</li>`)
    .join('');
  const rv = c.reconciliationReview;
  const review = rv
    ? `Review ${esc(rv.id)} by ${esc(rv.reviewedBy)} at ${esc(rv.reviewedAt)}, decision ${esc(rv.decision)}: ${rv.accepted ? '<strong>review record checks passed</strong>' : '<strong>review record checks FAILED, acceptance NOT established</strong>'}.`
    : '<strong>No reconciliation review record</strong>: acceptance NOT established.';
  const problems = c.reconciliationProblems.length
    ? `<p>Problems: ${esc(c.reconciliationProblems.join('; '))}.</p>`
    : '';
  return `<p>${head}</p>
<p>Reconciliation ${esc(rec.reconciliationId)} by ${esc(rec.reconciledBy)} at ${esc(rec.reconciledAt)}. Referenced authoritative-source evidence:</p>
<ul>${refs || '<li>none referenced</li>'}</ul>
<p>${review}</p>
${problems}<p class="muted">${esc(c.authenticationCaveat)}</p>`;
}

function coverageText(cov, report) {
  const c = report.coverage;
  const d = c.declaration;
  const decl = d
    ? `<p>Supplier declaration <strong>${esc(d.evidenceId)}</strong>, by ${esc(d.declaredBy)} at ${esc(d.declaredAt)}: &ldquo;${esc(d.statement)}&rdquo;</p>`
    : '<p><strong>No valid supplier declaration record</strong> (evidence ID, declarant, zoned timestamp and statement are all required).</p>';
  const label = c.declaredBasisLabel
    ? `<p class="muted">Basis label &ldquo;${esc(c.declaredBasisLabel)}&rdquo; is ignored as proof; only the records above count.</p>`
    : '';
  return `<p><strong>${esc(c.conclusion)}</strong> &middot; coverage class <strong>${esc(c.coverageClass)}</strong></p>
<p>${esc(c.reason)}</p>
<p>Channels in scope: ${esc(cov.channelsInScope.join(', '))}. Channels declared covered: ${esc(cov.channelsCovered.join(', '))}. Log window: ${esc(cov.windowStart)} to ${esc(cov.windowEnd)}.</p>
${decl}
${reconciliationHtml(c)}
${label}`;
}

function riskSection(caseData, report) {
  const r = report.risk;
  const banner = `<div class="banner">${esc(r.label)}</div>`;
  if (!r.appliesToThisLead) {
    return `${banner}<p class="suppressed"><strong>No lead-specific estimate shown.</strong> ${esc(r.suppressedReason)}</p>
<p>Formula (not applied): <code>${esc(r.formula)}</code></p>`;
  }
  const rows = Object.entries(caseData.riskAssumptions)
    .map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(v.value)}</td><td>${esc(v.basis)}</td></tr>`)
    .join('\n');
  return `${banner}
<div class="table-wrap"><table><thead><tr><th>Assumption</th><th>Value</th><th>Basis</th></tr></thead><tbody>
${rows}
</tbody></table></div>
<p>Formula: <code>${esc(r.formula)}</code></p>
<p>Expected gross margin if timely: ${usd(r.expectedGrossMarginIfTimelyUsd)}. Illustrative at-risk gross margin: <strong>${usd(r.illustrativeAtRiskGrossMarginUsd)}</strong>.</p>`;
}

export function renderReport(caseData, report) {
  const s = report.sla;
  const slaRows = [
    ['Lead created', `${s.createdAt} (${s.evidenceIds[0]})`],
    ['First contact', s.firstContactAt ? `${s.firstContactAt}, ${s.firstContactChannel} (${s.evidenceIds.at(-1)})` : 'none found'],
    ['Elapsed', s.elapsedMinutes == null ? 'n/a' : mins(s.elapsedMinutes)],
    ['SLA', mins(s.slaMinutes)],
    ['Over SLA', mins(s.breachMinutes)],
    ['SLA status (timing only)', s.status],
  ]
    .map(([k, v]) => `<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`)
    .join('\n');
  const warn = report.synthetic
    ? '<span class="badge">SYNTHETIC DEMO DATA</span>'
    : '<span class="badge">NOT MARKED SYNTHETIC: review data handling before sharing</span>';
  return `<header>${warn}
<h1>Lead-Path Revenue Leak Evidence Sprint: Sample Report</h1>
<p class="muted">Prepared by [Your Agency] for client ${esc(caseData.client?.name)}. Agency in this demo: ${esc(caseData.agency?.name)}. ${esc(caseData.notice)}</p>
</header>
<h2>1. Finding</h2>
<p class="verdict">Verdict: <strong>${esc(report.verdict)}</strong>${report.confirmationBasis ? ` (basis: ${esc(report.confirmationBasis)})` : ''}</p>
<p>${esc(report.summary)}</p>
<p>Evidence cited: ${esc(s.evidenceIds.join(', '))}.</p>
<h2>2. Evidence timeline</h2>
<div class="table-wrap"><table><thead><tr><th>ID</th><th>Source</th><th>Timestamp (UTC)</th><th>Event</th></tr></thead><tbody>
${timeline(caseData, report)}
</tbody></table></div>
<h2>3. SLA check</h2>
<p>SLA definition: ${esc(caseData.sla.definition)}</p>
<div class="table-wrap"><table><tbody>
${slaRows}
</tbody></table></div>
<h2>4. Contact-log coverage</h2>
${coverageText(caseData.coverage, report)}
<h2>5. Illustrative risk calculation</h2>
${riskSection(caseData, report)}
<h2>6. What this does / does not establish</h2>
<div class="box">
<p><strong>Establishes:</strong> given the supplied records, the timing of first outbound contact versus the stated SLA, and whether the stated coverage supports "no earlier contact".</p>
<p><strong>Does not establish:</strong> realized loss, that the delay caused any lost sale, recovered revenue, any guarantee, the accuracy of agency-supplied assumptions, or that the supplier's coverage declaration is true. Even an accepted reconciliation is checked for presence and links only: this software does not authenticate provider artifacts or reviewer identity.</p>
</div>`;
}
