'use strict';
// Pure rendering: sessions in, one line per project out. Stages come from the injected roadmap(root) lookup.
// Every field read from disk is re-sanitized here.
const path = require('path');
const crypto = require('crypto');
const { clean } = require('./sanitize');

const STALE_ACTIVE_MS = 2 * 3600000; // an "active" session silent this long is shown as waiting
const ENDED_VISIBLE_MS = 24 * 3600000;
const MAX_LINES = 15;
const LINE_COLORS = [33, 196, 34, 208, 129, 37, 166, 27, 162, 100]; // one per line, like a real map
const STATUSES = ['active', 'idle', 'ended']; // also the sort order
const GLYPH = { done: '●', now: '◉', todo: '○' };

const TEXT = {
  en: {
    title: 'METROLINE', projects: (n, a) => `${n} project${n === 1 ? '' : 's'} · ${a} running`,
    empty: 'No sessions recorded yet. Start working in any Claude Code session.',
    active: 'running', idle: 'waiting for you', ended: 'ended', sessions: (n) => `${n} sessions`,
    noPlan: 'no plan · run /metroline:plan in this project', recent: 'recent', allDone: 'all stages done',
    more: (n) => `+${n} more (use --all)`, updatedAt: (hm) => `updated ${hm} · refreshes every 5 s`,
    remove: 'remove', removeConfirm: 'Remove from the map (project files stay)',
    just: 'just now', min: (n) => `${n}m ago`, hour: (n) => `${n}h ago`, day: (n) => `${n}d ago`,
  },
  ko: {
    title: 'METROLINE', projects: (n, a) => `프로젝트 ${n}개 · 진행 중 ${a}개`,
    empty: '기록된 세션이 없습니다. Claude Code 세션에서 작업을 시작하면 노선이 생깁니다.',
    active: '진행 중', idle: '입력 대기', ended: '종료', sessions: (n) => `세션 ${n}개`,
    noPlan: '계획 없음 · 이 프로젝트에서 /metroline:plan 실행', recent: '최근', allDone: '모든 단계 완료',
    more: (n) => `외 ${n}개 (--all 로 전체 보기)`, updatedAt: (hm) => `${hm} 갱신 · 5초마다 새로고침`,
    remove: '삭제', removeConfirm: '노선에서 지우기 (프로젝트 파일은 그대로)',
    just: '방금', min: (n) => `${n}분 전`, hour: (n) => `${n}시간 전`, day: (n) => `${n}일 전`,
  },
};

function pickLang(env) {
  const v = String(env.METROLINE_LANG || env.LC_ALL || env.LC_MESSAGES || env.LANG || '').toLowerCase();
  return v.startsWith('ko') ? 'ko' : 'en';
}

function ago(ms, t) {
  const m = Math.floor(Math.max(0, ms) / 60000);
  if (m < 1) return t.just;
  if (m < 60) return t.min(m);
  if (m < 1440) return t.hour(Math.floor(m / 60));
  return t.day(Math.floor(m / 1440));
}

// Merge sessions that share a project root. The project takes its liveliest status and latest activity.
// Unknown shapes degrade, never throw. v0.1 files have cwd instead of root.
function group(sessions, now) {
  const projects = new Map();
  for (const raw of sessions) {
    const root = [raw.root, raw.cwd].find((p) => typeof p === 'string' && path.isAbsolute(p)) || '';
    const key = root || clean(raw.project, 40);
    if (!key) continue;
    const updated = Number.isFinite(raw.updated) ? raw.updated : 0;
    let status = STATUSES.includes(raw.status) ? raw.status : 'idle';
    if (status === 'active' && now - updated > STALE_ACTIVE_MS) status = 'idle';
    let p = projects.get(key);
    if (!p) {
      p = { root, name: clean(path.basename(root), 40) || clean(raw.project, 40) || '?', status, updated, live: 0, lastPrompt: '', promptAt: -Infinity };
      projects.set(key, p);
    }
    if (STATUSES.indexOf(status) < STATUSES.indexOf(p.status)) p.status = status;
    p.updated = Math.max(p.updated, updated);
    if (status !== 'ended') p.live++;
    const prompts = Array.isArray(raw.prompts) ? raw.prompts.filter((x) => x && typeof x === 'object') : [];
    const last = prompts[prompts.length - 1];
    const at = last && Number.isFinite(last.t) ? last.t : updated;
    if (last && at > p.promptAt) {
      p.promptAt = at;
      p.lastPrompt = clean(last.text, 80);
    }
  }
  return [...projects.values()];
}

// 기획 ●━━ 설계 ◉── 구현 ○ : heavy track behind a finished stage, thin track ahead.
function track(stages, paint) {
  return stages.map((s, i) => {
    const link = i === stages.length - 1 ? '' : s.state === 'done' ? paint('━━') : '──';
    return `${s.name} ${s.state === 'todo' ? GLYPH.todo : paint(GLYPH[s.state])}${link}`;
  }).join(' ');
}

// Current stage (in progress, else first unfinished), its current task, task counts and the next stage.
// null when every stage is done.
function position(stages) {
  let i = stages.findIndex((s) => s.state === 'now');
  if (i < 0) i = stages.findIndex((s) => s.state !== 'done');
  if (i < 0) return null;
  const tasks = stages[i].tasks;
  return {
    stage: stages[i],
    task: tasks.find((k) => k.state === 'now') || tasks.find((k) => k.state !== 'done'),
    done: tasks.filter((k) => k.state === 'done').length,
    total: tasks.length,
    next: stages[i + 1],
  };
}

// "Design: API spec (1/3)"
function current(stages, t) {
  const p = position(stages);
  if (!p) return t.allDone;
  if (!p.total) return p.stage.name;
  return `${p.stage.name}${p.task ? ': ' + p.task.name : ''} (${p.done}/${p.total})`;
}

function order(a, b) {
  return STATUSES.indexOf(a.status) - STATUSES.indexOf(b.status) || b.updated - a.updated;
}

// Shared by the text and HTML views: grouped, filtered, sorted and capped projects with their stages.
function prepare(sessions, o) {
  const now = o.now || Date.now();
  const roadmap = o.roadmap || (() => null);
  let lines = group(sessions, now);
  if (!o.all) lines = lines.filter((l) => l.status !== 'ended' || now - l.updated < ENDED_VISIBLE_MS);
  lines.sort(order);
  const hidden = o.all ? 0 : Math.max(0, lines.length - MAX_LINES);
  if (hidden) lines = lines.slice(0, MAX_LINES);
  for (const l of lines) l.stages = (l.root && roadmap(l.root)) || [];
  return { now, lines, hidden, active: lines.filter((l) => l.status === 'active').length };
}

// "▶ running · 2m ago · 2 sessions"
function meta(l, t, now) {
  const mark = l.status === 'active' ? '▶' : l.status === 'idle' ? '‖' : '■';
  const parts = [`${mark} ${t[l.status]}`, ago(now - l.updated, t)];
  if (l.live > 1) parts.push(t.sessions(l.live));
  return parts.join(' · ');
}

function render(sessions, opts) {
  const o = opts || {};
  const t = TEXT[o.lang] || TEXT.en;
  const color = !!o.color;
  const sgr = (code, s) => (color ? `\u001b[${code}m${s}\u001b[0m` : s);
  const bold = (s) => sgr('1', s);
  const dim = (s) => sgr('2', s);

  const { now, lines, hidden, active } = prepare(sessions, o);
  if (!lines.length) return bold(t.title) + '\n\n' + t.empty + '\n';

  const out = [bold(t.title) + '  ' + dim(t.projects(lines.length + hidden, active)), ''];
  lines.forEach((l, i) => {
    const paint = (s) => (l.status === 'ended' ? dim(s) : sgr('38;5;' + LINE_COLORS[i % LINE_COLORS.length], s));
    out.push(`${paint('━━')} ${bold(l.name)}   ${meta(l, t, now)}`);
    if (!l.stages.length) {
      out.push('   ' + dim(t.noPlan));
      if (l.lastPrompt) out.push(dim(`   ${t.recent}: “${l.lastPrompt}”`));
    } else {
      out.push('   ' + track(l.stages, paint));
      if (o.detail) {
        for (const s of l.stages) {
          out.push(`   ${GLYPH[s.state]} ${s.name}`);
          for (const k of s.tasks) out.push(dim(`      ${GLYPH[k.state]} ${k.name}`));
        }
      } else {
        out.push(`   └ ${current(l.stages, t)}`);
      }
    }
    out.push('');
  });
  if (hidden) out.push(dim(t.more(hidden)), '');
  return out.join('\n');
}

// HTML escaping: every piece of text from disk passes through this before it enters markup.
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
const HEX = ['#0052a4', '#00a84d', '#ef7c1c', '#00a5de', '#996cac', '#cd7c2f', '#747f00', '#e6186c', '#bdb092', '#77c4a3'];

// Subway wording for the web view only; the terminal view keeps the plain words.
const SIGN = {
  en: {
    active: 'In service', idle: 'Stopped · waiting for you', ended: 'Out of service', trains: (n) => `${n} trains`,
    line: (n) => `Line ${n}`, thisStop: 'This stop', next: 'Next', terminus: 'Terminus reached · all stages done 🎉',
    construction: 'Line under construction', open: 'run /metroline:plan to open it', recent: 'Last request',
    close: 'Close line', closeConfirm: 'Close this line (project files stay)',
  },
  ko: {
    active: '운행 중', idle: '정차 중 · 입력 대기', ended: '운행 종료', trains: (n) => `열차 ${n}대`,
    line: (n) => `${n}호선`, thisStop: '이번 역', next: '다음 역', terminus: '종착역 도착 · 모든 단계 완료 🎉',
    construction: '노선 공사 중', open: '/metroline:plan 으로 개통하기', recent: '최근 요청',
    close: '폐선', closeConfirm: '이 노선 폐선하기 (프로젝트 파일은 그대로)',
  },
};

const CSS = `
:root{--bg:#eef1f5;--paper:#fff;--ink:#1b2430;--muted:#7b8794;--grid:rgba(27,36,48,.05);--sign:#0b3d91;--board:#15181d;--led:#ffb43b}
@media (prefers-color-scheme:dark){:root{--bg:#0e131a;--paper:#18202a;--ink:#e8edf2;--muted:#8b98a6;--grid:rgba(255,255,255,.04);--sign:#123f8f;--board:#07090c}}
*{box-sizing:border-box}
body{margin:0;padding:20px 16px 32px;color:var(--ink);background:var(--bg);background-image:linear-gradient(var(--grid) 1px,transparent 1px),linear-gradient(90deg,var(--grid) 1px,transparent 1px);background-size:24px 24px;font:15px/1.5 system-ui,-apple-system,"Segoe UI","Malgun Gothic",sans-serif}
main{max-width:980px;margin:0 auto}
.sign{display:flex;align-items:center;gap:14px;background:var(--sign);color:#fff;border-radius:18px;padding:14px 18px;margin-bottom:18px;box-shadow:0 8px 20px rgba(11,61,145,.25)}
.logo{flex:none;width:42px;height:42px;border-radius:50%;background:#fff;color:var(--sign);font-weight:900;font-size:22px;display:grid;place-items:center}
h1{font-size:19px;letter-spacing:.14em;margin:0;line-height:1.2}
.sign p{margin:0;opacity:.85;font-size:13px}
.clock{margin-left:auto;font:700 20px ui-monospace,Consolas,monospace;background:rgba(0,0,0,.25);padding:4px 10px;border-radius:8px;color:var(--led)}
.card{background:var(--paper);border-radius:20px;padding:16px 20px 16px;margin-bottom:14px;box-shadow:0 1px 0 rgba(0,0,0,.03),0 8px 22px rgba(20,30,50,.07)}
.card.ended{opacity:.6}
.head{display:flex;align-items:center;gap:8px 10px;flex-wrap:wrap}
.badge{flex:none;min-width:30px;height:30px;padding:0 9px;border-radius:15px;background:var(--c);color:#fff;font-weight:800;font-size:13px;display:grid;place-items:center;box-shadow:0 0 0 3px var(--paper),0 0 0 5px var(--c)}
.title{font-size:18px;font-weight:800;margin:0 2px}
.pill{font-size:12px;font-weight:700;padding:3px 10px 3px 8px;border-radius:999px;display:inline-flex;align-items:center;gap:6px}
.pill::before{content:"";width:7px;height:7px;border-radius:50%;background:currentColor}
.pill.active{background:rgba(34,197,94,.15);color:#16a34a}
.pill.active::before{animation:blink 1.4s ease-in-out infinite}
.pill.idle{background:rgba(245,158,11,.16);color:#c27803}
.pill.ended{background:rgba(120,130,140,.16);color:var(--muted)}
.meta{color:var(--muted);font-size:13px}
ol{list-style:none;display:flex;margin:14px 0 2px;padding:0 0 4px;overflow-x:auto}
li{flex:1;min-width:86px;position:relative;text-align:center;padding-top:30px}
li:not(:last-child)::after{content:"";position:absolute;top:41px;left:50%;width:100%;height:8px;margin-top:-4px;background:var(--c);opacity:.2;border-radius:4px}
li.done:not(:last-child)::after{opacity:1}
.dot{position:relative;z-index:1;display:block;width:22px;height:22px;margin:0 auto 7px;border-radius:50%;background:var(--paper);border:5px solid var(--c)}
.todo .dot{border-color:color-mix(in srgb,var(--c) 30%,var(--paper))}
.now .dot{width:30px;height:30px;margin-top:-4px;margin-bottom:3px;border-width:7px;box-shadow:0 0 0 5px color-mix(in srgb,var(--c) 22%,transparent)}
.active .now .dot{animation:ring 1.8s ease-out infinite}
.train{position:absolute;top:0;left:50%;transform:translateX(-50%);font-size:22px;line-height:1;z-index:2}
.active .train{animation:bob 1.1s ease-in-out infinite}
.ended .train{display:none}
.name{display:block;font-size:13px;font-weight:600;padding:0 4px;word-break:keep-all}
.now .name{font-weight:800}
.todo .name{color:var(--muted)}
.board{margin-top:12px;display:flex;flex-wrap:wrap;gap:4px 18px;background:var(--board);background-image:radial-gradient(rgba(255,255,255,.06) 1px,transparent 1px);background-size:3px 3px;color:var(--led);border-radius:10px;padding:9px 14px;font:600 13px/1.45 ui-monospace,Consolas,"Malgun Gothic",monospace}
.board .k{opacity:.65;margin-right:6px}
.board b{color:#fff7e6}
.works{margin:20px 0 10px;height:10px;border-radius:5px;background:repeating-linear-gradient(-45deg,#f5b400 0 10px,#2b2b2b 10px 20px);opacity:.85}
.hint{margin:6px 0 0;color:var(--muted);font-size:13px}
.rm{margin-left:auto;font-size:12px}
.rm summary{cursor:pointer;list-style:none;color:var(--muted);border:1px solid color-mix(in srgb,var(--muted) 40%,transparent);border-radius:999px;padding:2px 10px}
.rm summary::-webkit-details-marker{display:none}
.rm form{display:inline;margin-left:6px}
.rm button{font:inherit;font-weight:700;color:#fff;background:#e6186c;border:0;border-radius:999px;padding:3px 12px;cursor:pointer}
footer{margin-top:18px;color:var(--muted);font-size:12px;text-align:center}
@keyframes bob{50%{transform:translate(-50%,-4px)}}
@keyframes ring{0%{box-shadow:0 0 0 0 color-mix(in srgb,var(--c) 45%,transparent)}100%{box-shadow:0 0 0 12px transparent}}
@keyframes blink{50%{opacity:.25}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}`;

// The page's only script: reload every 5 s, except while a close confirmation is open.
// The CSP allows exactly this script by its hash; any other script, injected or not, is blocked.
const RELOAD = "setInterval(function(){if(!document.querySelector('details[open]'))location.reload()},5000)";
const RELOAD_HASH = crypto.createHash('sha256').update(RELOAD).digest('base64');

// Track with stations; a little train sits on the current one.
function stationsHtml(stages, s) {
  const p = position(stages);
  const items = stages.map((st) => {
    const tip = st.tasks.map((k) => `${GLYPH[k.state]} ${k.name}`).join('\n'); // hover shows the stage's tasks
    const train = p && st === p.stage ? '<span class="train">🚃</span>' : '';
    return `<li class="${st.state}"${tip ? ` title="${esc(tip)}"` : ''}>${train}<span class="dot"></span><span class="name">${esc(st.name)}</span></li>`;
  }).join('');
  let board;
  if (!p) {
    board = `<b>${esc(s.terminus)}</b>`;
  } else {
    const task = p.total ? ` › ${esc(p.task ? p.task.name : '')} (${p.done}/${p.total})` : '';
    board = `<span><span class="k">${esc(s.thisStop)}</span><b>${esc(p.stage.name)}</b>${task}</span>`
      + (p.next ? `<span><span class="k">${esc(s.next)}</span>${esc(p.next.name)}</span>` : '');
  }
  return `<ol>${items}</ol><div class="board">${board}</div>`;
}

// Standalone page with no external requests (the CSP enforces it).
// opts.removeUrl (local server only) adds a two-click "close line" button to each project.
function renderHtml(sessions, opts) {
  const o = opts || {};
  const t = TEXT[o.lang] || TEXT.en;
  const s = SIGN[o.lang] || SIGN.en;
  const { now, lines, hidden, active } = prepare(sessions, o);
  const cards = lines.map((l, i) => {
    const meta = [ago(now - l.updated, t)];
    if (l.live > 1) meta.push(s.trains(l.live));
    const rm = o.removeUrl && l.root
      ? `<details class="rm"><summary>${esc(s.close)}</summary><form method="post" action="${esc(o.removeUrl)}"><input type="hidden" name="root" value="${esc(l.root)}"><button>${esc(s.closeConfirm)}</button></form></details>`
      : '';
    const body = l.stages.length
      ? stationsHtml(l.stages, s)
      : `<div class="works"></div><p class="hint">🚧 ${esc(s.construction)} · ${esc(s.open)}</p>`
        + (l.lastPrompt ? `<p class="hint">${esc(s.recent)}: “${esc(l.lastPrompt)}”</p>` : '');
    return `<section class="card ${l.status}" style="--c:${HEX[i % HEX.length]}"><div class="head">`
      + `<span class="badge">${esc(s.line(i + 1))}</span><span class="title">${esc(l.name)}</span>`
      + `<span class="pill ${l.status}">${esc(s[l.status])}</span><span class="meta">${esc(meta.join(' · '))}</span>${rm}</div>${body}</section>`;
  });
  const stamp = new Date(now).toTimeString().slice(0, 5);
  return `<!doctype html>
<html lang="${o.lang === 'ko' ? 'ko' : 'en'}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'sha256-${RELOAD_HASH}'; form-action 'self'">
<title>Metroline</title><style>${CSS}</style></head>
<body><main>
<header class="sign"><span class="logo">M</span><div><h1>${esc(t.title)}</h1><p>${esc(lines.length ? t.projects(lines.length + hidden, active) : t.empty)}</p></div><span class="clock">${esc(stamp)}</span></header>
${cards.join('\n')}
${hidden ? `<p class="hint">${esc(t.more(hidden))}</p>` : ''}
<footer>${esc(t.updatedAt(stamp))}</footer></main><script>${RELOAD}</script></body></html>
`;
}

module.exports = { render, renderHtml, pickLang };
