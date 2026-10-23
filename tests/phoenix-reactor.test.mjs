import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { extractAuthUrl, sanitizeCode, envConflicts } from '../ops/phoenix-reactor/lib/claude-auth.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'ops', 'phoenix-reactor');
const URL1 = 'https://claude.com/cai/oauth/authorize?code=true&client_id=abc&redirect_uri=https%3A%2F%2Fplatform.claude.com%2Foauth%2Fcode%2Fcallback&state=XYZ-123_';

test('extractAuthUrl re-joins a hard-wrapped URL and stops at the prompt', () => {
  const wrapped = 'Opening browser…\nIf the browser didn\'t open, visit: ' + URL1.slice(0, 40) + '\n' + URL1.slice(40, 90) + '\n' + URL1.slice(90) + '\nPaste code here if prompted >';
  assert.equal(extractAuthUrl(wrapped), URL1);
});
test('extractAuthUrl returns null when no authorize URL exists', () => {
  assert.equal(extractAuthUrl('nothing here'), null);
  assert.equal(extractAuthUrl('https://example.com/oauth/authorize?x=1'), null);
});
test('sanitizeCode strips whitespace, zero-width characters and quotes', () => {
  assert.equal(sanitizeCode(' "abcdefghij​klmnopqrstuvwxyz#st ate12"\n'), 'abcdefghijklmnopqrstuvwxyz#state12');
});
test('sanitizeCode refuses a pasted URL, truncated, empty and hostile input', () => {
  assert.throws(() => sanitizeCode(URL1), /PASTED_URL_NOT_CODE/);
  assert.throws(() => sanitizeCode('abc#def'), /TOO_SHORT/);
  assert.throws(() => sanitizeCode('   '), /EMPTY_CODE/);
  assert.throws(() => sanitizeCode('aaaaaaaaaaaaaaaaaaaaaaaa; rm -rf /'), /INVALID_CHARACTERS/);
});
test('envConflicts lists override names only, never values', () => {
  const r = envConflicts({ ANTHROPIC_API_KEY: 'sk-secret', ANTHROPIC_BASE_URL: '', PATH: '/x' });
  assert.deepEqual(r, ['ANTHROPIC_API_KEY']);
  assert.ok(!JSON.stringify(r).includes('sk-secret'));
});
for (const script of ['smoke.sh', 'auth-flow.sh']) {
  test(`phoenix-reactor ${script}`, (t) => {
    const r = spawnSync('bash', [path.join(root, 'tests', script)], { encoding: 'utf8', timeout: 150000 });
    if (r.status === 77) return t.skip(r.stdout.trim());
    assert.equal(r.status, 0, r.stdout + r.stderr);
  });
}
