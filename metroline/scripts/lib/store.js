'use strict';
// One JSON file per session. No shared file, no network, no child processes.
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');

const SESSION_ID = /^[A-Za-z0-9_-]{1,64}$/;
const MAX_FILE_BYTES = 256 * 1024;
const MAX_FILES = 500;
const RETENTION_DAYS = 30;
const LOCK_STALE_MS = 5000;
const LOCK_WAIT_MS = 1500;

function dataDir() {
  // Fixed location so hooks and the terminal viewer always agree on where state lives.
  return path.resolve(process.env.METROLINE_HOME || path.join(os.homedir(), '.metroline'));
}

// Remember where the plugin is installed so a shell alias can find the viewer after updates.
function saveRoot(root) {
  if (typeof root !== 'string' || !path.isAbsolute(root) || root.length > 1000) return;
  ensureDir(dataDir());
  const file = path.join(dataDir(), 'root');
  try {
    if (fs.readFileSync(file, 'utf8') === root) return;
  } catch (_) {}
  const tmp = file + '.' + crypto.randomBytes(6).toString('hex') + '.tmp';
  fs.writeFileSync(tmp, root, { flag: 'wx', mode: 0o600 });
  fs.renameSync(tmp, file);
}

function sessionsDir() {
  return path.join(dataDir(), 'sessions');
}

// Create a private directory; refuse symlinks so writes cannot be redirected.
function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
  const st = fs.lstatSync(dir);
  if (st.isSymbolicLink() || !st.isDirectory()) throw new Error('unsafe data directory');
  if (process.platform !== 'win32' && (st.mode & 0o077) !== 0) fs.chmodSync(dir, 0o700);
  return dir;
}

function sessionFile(id) {
  if (typeof id !== 'string' || !SESSION_ID.test(id)) throw new Error('invalid session id');
  return path.join(sessionsDir(), id + '.json');
}

function readJson(file) {
  let st;
  try {
    st = fs.lstatSync(file);
  } catch (_) {
    return null;
  }
  if (!st.isFile() || st.size > MAX_FILE_BYTES) return null;
  try {
    const data = JSON.parse(fs.readFileSync(file, 'utf8'));
    return data && typeof data === 'object' && !Array.isArray(data) ? data : null;
  } catch (_) {
    return null;
  }
}

// Exclusive-create temp file, then rename: atomic, and never follows a planted symlink.
function writeJson(file, data) {
  const body = JSON.stringify(data);
  if (Buffer.byteLength(body) > MAX_FILE_BYTES) throw new Error('state too large');
  writeAtomic(file, body);
}

function writeAtomic(file, body) {
  const tmp = file + '.' + crypto.randomBytes(6).toString('hex') + '.tmp';
  const fd = fs.openSync(tmp, 'wx', 0o600);
  try {
    fs.writeSync(fd, body);
  } finally {
    fs.closeSync(fd);
  }
  try {
    fs.renameSync(tmp, file);
  } catch (err) {
    try { fs.unlinkSync(tmp); } catch (_) {}
    throw err;
  }
}

// The HTML view lives next to the session files. Hooks refresh it only once the user has created it.
function pageFile() {
  return path.join(dataDir(), 'metroline.html');
}

function hasPage() {
  try {
    return fs.lstatSync(pageFile()).isFile();
  } catch (_) {
    return false;
  }
}

function writePage(html) {
  ensureDir(dataDir());
  writeAtomic(pageFile(), html);
  return pageFile();
}

function sleep(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

// Parallel tool calls fire parallel hooks for the same session; serialize them.
function withLock(file, fn) {
  const lock = file + '.lock';
  const deadline = Date.now() + LOCK_WAIT_MS;
  for (;;) {
    try {
      fs.mkdirSync(lock, { mode: 0o700 });
      break;
    } catch (err) {
      if (err.code !== 'EEXIST') throw err;
      try {
        if (Date.now() - fs.lstatSync(lock).mtimeMs > LOCK_STALE_MS) fs.rmdirSync(lock);
      } catch (_) {}
      if (Date.now() > deadline) throw new Error('lock timeout');
      sleep(15);
    }
  }
  try {
    return fn();
  } finally {
    try { fs.rmdirSync(lock); } catch (_) {}
  }
}

function update(id, mutate) {
  ensureDir(dataDir());
  ensureDir(sessionsDir());
  const file = sessionFile(id);
  return withLock(file, () => {
    const next = mutate(readJson(file));
    if (next) writeJson(file, next);
    return next;
  });
}

function listFiles() {
  let names;
  try {
    if (fs.lstatSync(sessionsDir()).isSymbolicLink()) return [];
    names = fs.readdirSync(sessionsDir());
  } catch (_) {
    return [];
  }
  return names
    .filter((n) => n.endsWith('.json') && SESSION_ID.test(n.slice(0, -5)))
    .slice(0, MAX_FILES)
    .map((n) => path.join(sessionsDir(), n));
}

function list() {
  return listFiles().map(readJson).filter((s) => s && typeof s.id === 'string');
}

// Remove sessions idle longer than the retention window, plus orphaned temp/lock entries.
function prune(now) {
  const cutoff = (now || Date.now()) - RETENTION_DAYS * 86400000;
  let removed = 0;
  for (const file of listFiles()) {
    const s = readJson(file);
    const last = s && Number.isFinite(s.updated) ? s.updated : 0;
    if (last < cutoff) {
      try { fs.unlinkSync(file); removed++; } catch (_) {}
    }
  }
  let names = [];
  try { names = fs.readdirSync(sessionsDir()); } catch (_) {}
  for (const n of names) {
    if (!n.endsWith('.tmp') && !n.endsWith('.lock')) continue;
    const p = path.join(sessionsDir(), n);
    try {
      const st = fs.lstatSync(p);
      if (Date.now() - st.mtimeMs < 60000) continue;
      if (st.isDirectory()) fs.rmdirSync(p); else fs.unlinkSync(p);
    } catch (_) {}
  }
  return removed;
}

// Delete sessions: all, or only those that have ended.
function clear(onlyEnded) {
  let removed = 0;
  for (const file of listFiles()) {
    if (onlyEnded) {
      const s = readJson(file);
      if (s && s.status !== 'ended') continue;
    }
    try { fs.unlinkSync(file); removed++; } catch (_) {}
  }
  return removed;
}

// Take a project off the map: delete the session files recorded under its root.
// The project's own files, METROLINE.md included, are never touched. New activity there brings it back.
function removeProject(root) {
  if (typeof root !== 'string' || !root) return 0;
  let removed = 0;
  for (const file of listFiles()) {
    const s = readJson(file);
    if (!s || (s.root || s.cwd) !== root) continue;
    try { fs.unlinkSync(file); removed++; } catch (_) {}
  }
  return removed;
}

module.exports = { removeProject, pageFile, hasPage, writePage, saveRoot, update, list, prune, clear, SESSION_ID };
