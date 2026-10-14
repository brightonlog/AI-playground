#!/usr/bin/env node
'use strict';
// Local web view with remove buttons:  node serve.js [port]   (default 4647, 0 = any free port)
// A static file cannot change anything on disk, so removing a project needs this small server.
// It listens on 127.0.0.1 only and every request must carry the random token printed at start:
// other websites open in the same browser can neither read the map nor remove anything.
const http = require('http');
const crypto = require('crypto');
const store = require('./lib/store');
const roadmap = require('./lib/roadmap');
const { renderHtml, pickLang } = require('./lib/render');

const HOST = '127.0.0.1';
const MAX_BODY = 8192;
const arg = process.argv[2];
const wanted = arg === undefined ? 4647 : Number(arg);
if (!Number.isInteger(wanted) || wanted < 0 || wanted > 65535) {
  process.stderr.write('metroline: port must be 0-65535\n');
  process.exit(1);
}
const token = crypto.randomBytes(16).toString('hex');
let port;

function opts() {
  return { lang: pickLang(process.env), roadmap: roadmap.load, removeUrl: '/remove?t=' + token };
}

function send(res, status, body, headers) {
  res.writeHead(status, Object.assign({ 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store', 'X-Frame-Options': 'DENY' }, headers));
  res.end(body);
}

function tokenOk(value) {
  const a = Buffer.from(String(value || ''));
  const b = Buffer.from(token);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

function handle(req, res) {
  // The Host check stops DNS rebinding (a hostile domain pointed at 127.0.0.1); the token stops everything else.
  if (req.headers.host !== `${HOST}:${port}` && req.headers.host !== `localhost:${port}`) return send(res, 403, 'forbidden');
  const url = new URL(req.url, `http://${HOST}:${port}`);
  if (!tokenOk(url.searchParams.get('t'))) return send(res, 403, 'forbidden');

  if (req.method === 'GET' && url.pathname === '/') {
    return send(res, 200, renderHtml(store.list(), opts()), { 'Content-Type': 'text/html; charset=utf-8' });
  }
  if (req.method === 'POST' && url.pathname === '/remove') {
    let body = '';
    req.setEncoding('utf8');
    req.on('data', (chunk) => {
      body += chunk;
      if (body.length > MAX_BODY) req.destroy();
    });
    req.on('end', () => {
      try {
        store.removeProject(new URLSearchParams(body).get('root'));
        if (store.hasPage()) store.writePage(renderHtml(store.list(), Object.assign(opts(), { removeUrl: '' })));
        send(res, 303, '', { Location: '/?t=' + token }); // back to the map
      } catch (err) {
        send(res, 500, 'metroline: ' + err.message);
      }
    });
    return;
  }
  send(res, 404, 'not found');
}

const server = http.createServer((req, res) => {
  try {
    handle(req, res);
  } catch (err) {
    send(res, 500, 'metroline: ' + err.message); // a broken state file must not take the server down
  }
});
server.on('error', (err) => {
  process.stderr.write('metroline: ' + err.message + (err.code === 'EADDRINUSE' ? ' (try another port: serve.js 4648)' : '') + '\n');
  process.exit(1);
});

server.listen(wanted, HOST, () => {
  port = server.address().port;
  process.stdout.write(`metroline: open http://${HOST}:${port}/?t=${token}   (Ctrl+C to stop)\n`);
});
