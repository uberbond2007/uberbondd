// Browser entry: loads the synthetic case, builds the report with the same core as the tests, renders escaped HTML.
import { buildReport } from './sprint.mjs';
import { renderReport, esc } from './render.mjs';
const out = document.getElementById('report');
try {
  const res = await fetch('./synthetic-case.json', { cache: 'no-store' });
  if (!res.ok) throw new Error(`synthetic-case.json: HTTP ${res.status}`);
  const data = await res.json();
  out.innerHTML = renderReport(data, buildReport(data, data.lead.id));
} catch (err) {
  out.innerHTML = `<p class="error">Could not build the report: ${esc(err.message)}. Opened from file://? Browsers block module and JSON loading there; use serve.mjs.</p>`;
}
