// Local-only static server for demo.html (browsers block ES modules and fetch() over file://).
// Binds 127.0.0.1, serves only the files listed below from this directory, read-only. Stdlib only.
import http from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const dir = path.dirname(fileURLToPath(import.meta.url));
const port = Number(process.env.PORT ?? 8787);
const FILES = {
  '/demo.html': 'text/html; charset=utf-8',
  '/sprint.mjs': 'text/javascript; charset=utf-8',
  '/demo.mjs': 'text/javascript; charset=utf-8',
  '/render.mjs': 'text/javascript; charset=utf-8',
  '/synthetic-case.json': 'application/json; charset=utf-8',
};

http
  .createServer(async (req, res) => {
    const url = new URL(req.url, 'http://127.0.0.1');
    const name = url.pathname === '/' ? '/demo.html' : url.pathname;
    const type = FILES[name];
    if (req.method !== 'GET' || !type) {
      res.writeHead(404, { 'content-type': 'text/plain' }).end('not found');
      return;
    }
    const body = await readFile(path.join(dir, name.slice(1)));
    res.writeHead(200, {
      'content-type': type,
      'cache-control': 'no-store',
      'content-security-policy': "default-src 'self'; style-src 'unsafe-inline'; object-src 'none'; base-uri 'none'",
      'x-content-type-options': 'nosniff',
    }).end(body);
  })
  .listen(port, '127.0.0.1', () => console.log(`Synthetic demo: http://127.0.0.1:${port}/demo.html`));
