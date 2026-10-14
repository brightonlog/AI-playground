#!/usr/bin/env node
'use strict';
// Viewer. Two ways in:
//   terminal:  node metro.js [detail] [all] [watch] | html [all] | clear [all]
//   hook:      node metro.js --hook   (UserPromptExpansion; answers /metroline:map without a model turn)
// The map is shown to the user directly. It is never returned to the model as context.
const fs = require('fs');
const { pathToFileURL } = require('url');
const store = require('./lib/store');
const { render, renderHtml, pickLang } = require('./lib/render');
const roadmap = require('./lib/roadmap');

const WORDS = new Set(['detail', 'all', 'watch', 'html', 'clear', 'help']);
const HELP = [
  'metroline — subway map of your projects (stages from METROLINE.md)',
  '',
  '  (no args)    compact map',
  '  detail       list every stage and task',
  '  all          include ended and older projects',
  '  watch        redraw every 2s (terminal only)',
  '  html         write ~/.metroline/metroline.html; hooks keep it current from then on',
  '  clear        delete ended sessions      clear all: delete everything',
  '',
].join('\n');

// Only whitelisted words are honored; anything else is ignored.
function parse(args) {
  const flags = {};
  for (const a of args) {
    const w = String(a).toLowerCase().replace(/^--?/, '');
    if (WORDS.has(w)) flags[w] = true;
  }
  return flags;
}

function output(flags, color) {
  const opts = { lang: pickLang(process.env), color, all: flags.all, detail: flags.detail, roadmap: roadmap.load };
  if (flags.help) return HELP;
  if (flags.clear) {
    const removed = store.clear(!flags.all);
    if (store.hasPage()) store.writePage(renderHtml(store.list(), opts));
    return `metroline: removed ${removed} session(s)\n`;
  }
  if (flags.html) return `metroline: open ${pathToFileURL(store.writePage(renderHtml(store.list(), opts))).href}\n`;
  return render(store.list(), opts);
}

function hook() {
  const input = JSON.parse(fs.readFileSync(0, 'utf8').slice(0, 65536));
  if (!input || input.hook_event_name !== 'UserPromptExpansion') return;
  const prompt = String(input.prompt || '').trim();
  if (!/(^|:)map$/.test(String(input.command_name || '')) || !prompt.startsWith('/metroline:map')) return;
  const flags = parse(String(input.command_args || '').split(/\s+/).slice(0, 8));
  delete flags.watch;
  // "block" stops the command before it reaches the model; "reason" is shown to the user only.
  process.stdout.write(JSON.stringify({ decision: 'block', reason: '\n' + output(flags, false) }));
}

function main() {
  const argv = process.argv.slice(2);
  if (argv.includes('--hook')) return hook();
  const flags = parse(argv);
  const color = process.stdout.isTTY && !process.env.NO_COLOR;
  if (!flags.watch || flags.clear || flags.help) return void process.stdout.write(output(flags, color) + '\n');
  const draw = () => process.stdout.write('\u001b[2J\u001b[H' + output(flags, color) + '\n');
  draw();
  setInterval(draw, 2000);
}

try {
  main();
} catch (err) {
  if (process.argv.includes('--hook')) process.exit(0); // never disturb the session
  process.stderr.write('metroline: ' + err.message + '\n');
  process.exit(1);
}
