// Pure helpers for the Claude Code subscription-login recovery flow.
// Kept side-effect free so tests/claude-auth.test.mjs can attack them directly.

const URL_RE = /https:\/\/claude\.(?:com|ai)\/[^\s"'<>]*oauth\/authorize\?[^\s"'<>]+/;

// Variables that outrank a subscription /login (official precedence order) or force API billing.
export const AUTH_OVERRIDE_VARS = [
  'CLAUDE_CODE_USE_BEDROCK',
  'CLAUDE_CODE_USE_VERTEX',
  'CLAUDE_CODE_USE_FOUNDRY',
  'ANTHROPIC_AUTH_TOKEN',
  'ANTHROPIC_API_KEY',
  'ANTHROPIC_BASE_URL',
];

/** Extract the single-line authorize URL from terminal text that may be hard-wrapped. */
export function extractAuthUrl(text) {
  const s = String(text ?? '');
  const direct = s.match(URL_RE);
  // Un-wrap: wrapped terminals insert newlines inside the URL. Re-join every line after the
  // first URL fragment until a line that clearly is not URL material.
  const start = s.search(/https:\/\/claude\.(?:com|ai)\//);
  if (start < 0) return null;
  let url = '';
  for (const line of s.slice(start).split('\n')) {
    const t = line.replace(/\r/g, '').trim();
    if (!t || /\s/.test(t)) {
      if (url) break;
      continue;
    }
    url += t;
  }
  const m = url.match(URL_RE);
  return m ? m[0] : direct ? direct[0] : null;
}

/** Normalise a pasted authorization code; throws a precise Error describing the paste defect. */
export function sanitizeCode(raw) {
  let c = String(raw ?? '')
    .replace(/[​-‍⁠﻿]/g, '')
    .replace(/\s+/g, '')
    .replace(/^["'`]+|["'`]+$/g, '');
  if (!c) throw new Error('EMPTY_CODE');
  if (/^https?:/i.test(c) || c.includes('oauth/authorize')) throw new Error('PASTED_URL_NOT_CODE');
  if (!/^[A-Za-z0-9_#.~-]+$/.test(c)) throw new Error('CODE_HAS_INVALID_CHARACTERS');
  if (c.length < 20) throw new Error('CODE_TOO_SHORT_LIKELY_TRUNCATED');
  return c;
}

/** Report env vars that would override or bypass subscription login. Values are never returned. */
export function envConflicts(env = process.env) {
  return AUTH_OVERRIDE_VARS.filter((k) => env[k] !== undefined && env[k] !== '');
}

const [, , cmd, ...args] = process.argv;
if (import.meta.url === `file://${process.argv[1]}`) {
  const read = async () => {
    const chunks = [];
    for await (const ch of process.stdin) chunks.push(ch);
    return Buffer.concat(chunks).toString('utf8');
  };
  try {
    if (cmd === 'url') {
      const u = extractAuthUrl(await read());
      if (!u) process.exit(2);
      console.log(u);
    } else if (cmd === 'code') {
      console.log(sanitizeCode(args.length ? args.join(' ') : await read()));
    } else if (cmd === 'conflicts') {
      console.log(envConflicts().join(' '));
    } else {
      console.error('usage: claude-auth.mjs url|code|conflicts');
      process.exit(64);
    }
  } catch (e) {
    console.error(e.message);
    process.exit(3);
  }
}
