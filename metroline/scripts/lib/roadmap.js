'use strict';
// METROLINE.md parser. Unindented checklist items are stages; indented items are that stage's tasks.
// Every other line is ignored, so the file can carry headings and notes.
const fs = require('fs');
const path = require('path');
const { clean } = require('./sanitize');

const FILE = 'METROLINE.md';
const MAX_STAGES = 12;
const MAX_TASKS = 30;
const MAX_CHARS = 60;
const MAX_BYTES = 64 * 1024;
const ITEM = /^([ \t]*)[-*+][ \t]+\[([ xX>~\/])\][ \t]+(.+)$/;
const STATE = { ' ': 'todo', x: 'done', X: 'done', '>': 'now', '~': 'now', '/': 'now' };

function parse(text) {
  const stages = [];
  let stage = null; // stage that indented items attach to; null past the cap or before the first stage
  for (const line of String(text).split(/\r?\n/)) {
    const m = ITEM.exec(line);
    const name = m && clean(m[3], MAX_CHARS);
    if (!name) continue;
    const item = { name, state: STATE[m[2]] };
    if (!m[1]) {
      stage = stages.length < MAX_STAGES ? Object.assign(item, { tasks: [] }) : null;
      if (stage) stages.push(stage);
    } else if (stage && stage.tasks.length < MAX_TASKS) {
      stage.tasks.push(item);
    }
  }
  // A "[ ]" stage takes its state from its tasks: all done = done, any started = in progress.
  for (const s of stages) {
    if (s.state !== 'todo' || !s.tasks.length) continue;
    if (s.tasks.every((k) => k.state === 'done')) s.state = 'done';
    else if (s.tasks.some((k) => k.state !== 'todo')) s.state = 'now';
  }
  return stages;
}

// mtime cache: the watch view redraws every 2 s, but a file is re-read only when it changes.
const cache = new Map(); // root -> { mtimeMs, size, stages }

// Stages for a project root, or null when it has no readable METROLINE.md.
function load(root) {
  if (typeof root !== 'string' || !path.isAbsolute(root)) return null;
  let st;
  try {
    st = fs.lstatSync(path.join(root, FILE));
  } catch (_) {
    cache.delete(root);
    return null;
  }
  if (!st.isFile() || st.size > MAX_BYTES) return null; // symlinks and oversized files are refused
  const hit = cache.get(root);
  if (hit && hit.mtimeMs === st.mtimeMs && hit.size === st.size) return hit.stages;
  let stages;
  try {
    stages = parse(fs.readFileSync(path.join(root, FILE), 'utf8').slice(0, MAX_BYTES));
  } catch (_) {
    return null;
  }
  cache.set(root, { mtimeMs: st.mtimeMs, size: st.size, stages });
  return stages;
}

module.exports = { parse, load, FILE };
