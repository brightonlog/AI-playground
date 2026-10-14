#!/usr/bin/env node
'use strict';
// Hook entry point. Reads one hook event from stdin and updates that session's state file.
// Contract: always exits 0, and prints nothing to stdout (stdout becomes model context on some events)
// except the SessionStart plan reminder, a JSON systemMessage that only the user sees.
let fs, os, path, store, clean, safeText;
try {
  fs = require('fs');
  os = require('os');
  path = require('path');
  store = require('./lib/store');
  ({ clean, safeText } = require('./lib/sanitize'));
} catch (_) {
  process.exit(0); // a broken install must never break the session
}

const MAX_STDIN = 1024 * 1024;
const MAX_PROMPTS = 30;
const PROMPT_CHARS = 80;
const MARKERS = ['METROLINE.md', '.git'];

function readStdin() {
  const chunks = [];
  const buf = Buffer.alloc(65536);
  let total = 0;
  for (;;) {
    let n;
    try {
      n = fs.readSync(0, buf, 0, buf.length, null);
    } catch (err) {
      if (err.code === 'EAGAIN') continue;
      if (err.code === 'EOF') break;
      throw err;
    }
    if (n === 0) break;
    total += n;
    if (total > MAX_STDIN) throw new Error('input too large');
    chunks.push(Buffer.from(buf.subarray(0, n)));
  }
  return Buffer.concat(chunks).toString('utf8');
}

// Plugin userConfig booleans arrive as CLAUDE_PLUGIN_OPTION_<NAME>; both options default to on.
function optionOn(name) {
  const v = String(process.env['CLAUDE_PLUGIN_OPTION_' + name] || '').toLowerCase();
  return !(v === 'false' || v === '0' || v === 'no' || v === 'off');
}

function capturePrompts() {
  return optionOn('CAPTURE_PROMPTS');
}

// At session start in a project without METROLINE.md, suggest /metroline:plan.
// systemMessage is shown to the user only; it never enters model context.
function remindPlan(root) {
  if (!root || !optionOn('PLAN_REMINDER') || fs.existsSync(path.join(root, 'METROLINE.md'))) return;
  const text = require('./lib/render').pickLang(process.env) === 'ko'
    ? 'Metroline: 이 프로젝트에 계획이 없습니다. /metroline:plan 으로 단계를 만들 수 있습니다.'
    : 'Metroline: this project has no plan. Run /metroline:plan to create its stages.';
  fs.writeSync(1, JSON.stringify({ systemMessage: text })); // sync write: the process exits right after
}

// Project root: CLAUDE_PROJECT_DIR when absolute, else cwd. A session started in a subfolder joins
// the nearest ancestor holding METROLINE.md or .git, so it shares that project's line.
function projectRoot(input) {
  const env = process.env.CLAUDE_PROJECT_DIR;
  const base = typeof env === 'string' && path.isAbsolute(env) ? env : input.cwd;
  if (typeof base !== 'string' || !path.isAbsolute(base)) return '';
  const home = os.homedir(); // a dotfiles repo in ~ must not swallow every project
  for (let dir = path.resolve(base); ; dir = path.dirname(dir)) {
    if (dir !== home && MARKERS.some((m) => fs.existsSync(path.join(dir, m)))) return dir;
    if (path.dirname(dir) === dir) return path.resolve(base);
  }
}

function apply(prev, input, now) {
  const state = prev && prev.v === 1 ? prev : { v: 1, id: input.session_id, started: now, status: 'idle' };
  state.prompts = Array.isArray(state.prompts) ? state.prompts.filter((x) => x && typeof x === 'object') : [];
  delete state.tasks; // v0.1 kept per-session task lists; stages now live in METROLINE.md
  delete state.cwd;
  state.updated = now;
  const root = clean(projectRoot(input));
  if (root && root.length <= 1000) {
    state.root = root;
    state.project = clean(path.basename(root), 40) || root.slice(0, 40);
  }
  if (typeof input.session_title === 'string') state.title = safeText(input.session_title, 60);

  switch (input.hook_event_name) {
    case 'SessionStart':
      if (state.status === 'ended') state.status = 'idle';
      break;
    case 'UserPromptSubmit': {
      state.status = 'active';
      const text = typeof input.prompt === 'string' ? input.prompt.trim() : '';
      if (text.startsWith('/metroline')) break;
      state.prompts.push({ t: now, text: capturePrompts() ? safeText(text, PROMPT_CHARS) : '' });
      if (state.prompts.length > MAX_PROMPTS) state.prompts = state.prompts.slice(-MAX_PROMPTS);
      break;
    }
    case 'PostToolUse': // task tool activity means the session is mid-turn
    case 'TaskCreated':
    case 'TaskCompleted':
      state.status = 'active';
      break;
    case 'Stop':
      state.status = 'idle';
      break;
    case 'SessionEnd':
      state.status = 'ended';
      break;
    default:
      return null;
  }
  return state;
}

function main() {
  const input = JSON.parse(readStdin());
  if (!input || typeof input !== 'object' || !store.SESSION_ID.test(String(input.session_id || ''))) return;
  if (input.agent_id) return; // subagent activity belongs to its parent's line
  const now = Date.now();
  const state = store.update(input.session_id, (prev) => apply(prev, input, now));
  if (input.hook_event_name === 'SessionStart') {
    remindPlan(state && state.root);
    store.prune(now);
    store.saveRoot(process.env.CLAUDE_PLUGIN_ROOT);
  }
  // Keep the HTML view current, but only once the user has opted in by running `metro html`.
  if (store.hasPage()) {
    const { renderHtml, pickLang } = require('./lib/render');
    store.writePage(renderHtml(store.list(), { lang: pickLang(process.env), now, roadmap: require('./lib/roadmap').load }));
  }
}

try {
  main();
} catch (err) {
  if (process.env.METROLINE_DEBUG) process.stderr.write('metroline: ' + err.message + '\n');
}
process.exit(0);
