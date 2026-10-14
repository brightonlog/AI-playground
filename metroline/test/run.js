'use strict';
// Zero-dependency tests: node test/run.js
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync, spawn } = require('child_process');
const { parse, load } = require('../scripts/lib/roadmap');
const { render } = require('../scripts/lib/render');

const ROOT = path.join(__dirname, '..');
const RECORD = path.join(ROOT, 'scripts', 'record.js');
const METRO = path.join(ROOT, 'scripts', 'metro.js');
let home;
let passed = 0;
let skipped = 0;

function fresh() {
  home = fs.mkdtempSync(path.join(os.tmpdir(), 'metroline-test-'));
  return home;
}
function env(extra) {
  // CLAUDE_PROJECT_DIR is cleared so a test run inside Claude Code does not leak its own project in.
  return Object.assign({}, process.env, { METROLINE_HOME: home, METROLINE_LANG: 'en', NO_COLOR: '1', CLAUDE_PROJECT_DIR: '', CLAUDE_PLUGIN_OPTION_PLAN_REMINDER: 'false' }, extra);
}
function hook(event, extra, envExtra) {
  const input = typeof event === 'string' ? JSON.stringify(Object.assign({ session_id: 's1', cwd: '/work/demo', hook_event_name: event }, extra)) : event.raw;
  const r = spawnSync('node', [RECORD], { input, env: env(envExtra), encoding: 'utf8' });
  assert.strictEqual(r.status, 0, 'hook must exit 0');
  assert.strictEqual(r.stdout, '', 'hook must print nothing to stdout');
  return r;
}
function state(id) {
  return JSON.parse(fs.readFileSync(path.join(home, 'sessions', (id || 's1') + '.json'), 'utf8'));
}
function metro(args, input, envExtra) {
  return spawnSync('node', [METRO].concat(args), { input, env: env(envExtra), encoding: 'utf8' });
}
// A project folder with an optional METROLINE.md, inside the test home.
function project(name, plan) {
  const dir = path.join(home, name);
  fs.mkdirSync(path.join(dir, 'sub'), { recursive: true });
  if (plan !== undefined) fs.writeFileSync(path.join(dir, 'METROLINE.md'), plan);
  return dir;
}
// Windows without developer mode cannot create symlinks; those tests are skipped there.
function trySymlink(target, link, type) {
  try {
    fs.symlinkSync(target, link, type);
    return true;
  } catch (err) {
    if (err.code !== 'EPERM') throw err;
    return false;
  }
}
function test(name, fn) {
  fresh();
  return Promise.resolve(fn()).then((r) => {
    if (r === 'skip') {
      skipped++;
      console.log('skip ' + name);
      return;
    }
    passed++;
    console.log('ok   ' + name);
  });
}

const PLAN = [
  '# Roadmap',
  '',
  '- [x] Plan',
  '- [>] Design',
  '  - [x] DB schema',
  '  - [>] API spec',
  '  - [ ] ERD',
  '- [ ] Build',
  '- [ ] Test',
  '- [ ] Deploy',
  'notes are ignored',
].join('\n');

(async () => {
  await test('roadmap parser reads stages, tasks and states', () => {
    const stages = parse(PLAN);
    assert.deepStrictEqual(stages.map((s) => [s.name, s.state, s.tasks.length]), [['Plan', 'done', 0], ['Design', 'now', 3], ['Build', 'todo', 0], ['Test', 'todo', 0], ['Deploy', 'todo', 0]]);
    assert.deepStrictEqual(stages[1].tasks.map((k) => k.state), ['done', 'now', 'todo']);
    assert.deepStrictEqual(parse('- [~] a\n- [/] b\n* [X] c\n\t- [ ] orphan-free\n').map((s) => s.state), ['now', 'now', 'done']);
    assert.deepStrictEqual(parse('  - [x] task before any stage\n- [ ] only').map((s) => s.tasks.length), [0]);
  });

  await test('a [ ] stage takes its state from its tasks', () => {
    const [allDone, started, untouched, empty] = parse('- [ ] a\n  - [x] 1\n  - [x] 2\n- [ ] b\n  - [x] 1\n  - [ ] 2\n- [ ] c\n  - [ ] 1\n- [ ] d\n');
    assert.deepStrictEqual([allDone.state, started.state, untouched.state, empty.state], ['done', 'now', 'todo', 'todo']);
    assert.strictEqual(parse('- [ ] a\n  - [>] 1\n')[0].state, 'now');
  });

  await test('roadmap caps stages, tasks and item length', () => {
    const many = Array.from({ length: 20 }, (_, i) => `- [ ] s${i}\n` + Array.from({ length: 40 }, (_, j) => `  - [ ] t${j}`).join('\n')).join('\n');
    const stages = parse(many + '\n- [ ] ' + 'x'.repeat(100));
    assert.strictEqual(stages.length, 12);
    assert.ok(stages.every((s) => s.tasks.length === 30));
    assert.strictEqual(Array.from(parse('- [ ] ' + '가'.repeat(100))[0].name).length, 60);
  });

  await test('roadmap is re-parsed only when mtime changes, oversized files are refused', () => {
    const dir = project('cached', '- [ ] one\n');
    const file = path.join(dir, 'METROLINE.md');
    const first = load(dir);
    assert.strictEqual(load(dir), first, 'unchanged file must come from the cache');
    fs.writeFileSync(file, '- [x] one\n');
    const later = new Date(Date.now() + 5000);
    fs.utimesSync(file, later, later);
    assert.strictEqual(load(dir)[0].state, 'done');
    fs.writeFileSync(file, '- [ ] big\n' + 'x'.repeat(65 * 1024));
    assert.strictEqual(load(dir), null);
    assert.strictEqual(load('relative/path'), null);
    assert.strictEqual(load(path.join(home, 'missing')), null);
  });

  await test('session flow records project root and status', () => {
    hook('SessionStart', { source: 'startup' }, { CLAUDE_PLUGIN_ROOT: ROOT });
    hook('UserPromptSubmit', { prompt: 'Design the ERD for the game' });
    assert.strictEqual(state().status, 'active');
    hook('Stop');
    assert.strictEqual(state().status, 'idle');
    hook('PostToolUse', { tool_name: 'TaskCreate', tool_input: { subject: 'Schema' }, tool_response: { task: { id: '1' } } });
    hook('TaskCompleted', { task_id: '1' });
    let s = state();
    assert.strictEqual(s.status, 'active');
    assert.strictEqual(s.project, 'demo');
    assert.strictEqual(s.root, path.resolve('/work/demo'));
    assert.ok(!('tasks' in s), 'task lists are no longer stored');
    hook('SessionEnd', { reason: 'other' });
    assert.strictEqual(state().status, 'ended');
    assert.strictEqual(fs.readFileSync(path.join(home, 'root'), 'utf8'), ROOT);
  });

  await test('sessions of one project, including subfolders, share one line', () => {
    const dir = project('music-game', PLAN);
    hook('UserPromptSubmit', { session_id: 's1', cwd: dir, prompt: 'a' });
    hook('UserPromptSubmit', { session_id: 's2', cwd: path.join(dir, 'sub'), prompt: 'b' });
    hook('Stop', { session_id: 's3', cwd: os.tmpdir() }, { CLAUDE_PROJECT_DIR: dir });
    for (const id of ['s1', 's2', 's3']) assert.strictEqual(state(id).root, dir);
    const map = metro([]).stdout;
    assert.ok(map.includes('1 project · 1 running'), map);
    assert.strictEqual(map.split('━━ music-game').length, 2, map);
    assert.ok(map.includes('▶ running · just now · 3 sessions'), map);
    assert.ok(map.includes('Plan ●━━ Design ◉── Build ○── Test ○── Deploy ○'), map);
    assert.ok(map.includes('└ Design: API spec (1/3)'), map);
    const detail = metro(['detail']).stdout;
    assert.ok(detail.includes('◉ Design') && detail.includes('○ ERD') && !detail.includes('└'), detail);
  });

  await test('a project without a plan shows the hint and the last request', () => {
    hook('UserPromptSubmit', { prompt: 'connect the calendar API' });
    hook('Stop');
    const map = metro([]).stdout;
    assert.ok(map.includes('━━ demo   ‖ waiting for you'), map);
    assert.ok(map.includes('no plan · run /metroline:plan in this project'), map);
    assert.ok(map.includes('recent: “connect the calendar API”'), map);
  });

  await test('plan reminder: user-only systemMessage at session start, only without a plan, can be turned off', () => {
    const run = (cwd, event, on) => spawnSync('node', [RECORD], { input: JSON.stringify({ session_id: 's1', cwd, hook_event_name: event }), env: env(on ? { CLAUDE_PLUGIN_OPTION_PLAN_REMINDER: 'true' } : {}), encoding: 'utf8' }).stdout;
    const bare = project('bare');
    const planned = project('planned', PLAN);
    const out = JSON.parse(run(bare, 'SessionStart', true));
    assert.deepStrictEqual(Object.keys(out), ['systemMessage']);
    assert.ok(out.systemMessage.includes('/metroline:plan'));
    assert.strictEqual(run(planned, 'SessionStart', true), '');
    assert.strictEqual(run(path.join(planned, 'sub'), 'SessionStart', true), '', 'subfolder sessions use the project plan');
    assert.strictEqual(run(bare, 'UserPromptSubmit', true), '', 'only at session start');
    assert.strictEqual(run(bare, 'SessionStart', false), '', 'off when plan_reminder is false');
  });

  await test('html view is opt-in, kept current by hooks, and escapes text', () => {
    const page = path.join(home, 'metroline.html');
    const dir = project("a&b'web", PLAN.replace('API spec', '<script>alert(1)</script>'));
    hook('UserPromptSubmit', { cwd: dir, prompt: '"><img src=x onerror=alert(1)>' });
    assert.ok(!fs.existsSync(page), 'hooks must not create the page on their own');
    assert.ok(metro(['html']).stdout.includes('file:///'));
    let html = fs.readFileSync(page, 'utf8');
    assert.ok(html.includes("default-src 'none'") && html.includes('a&#38;b&#39;web') && html.includes('&#60;script&#62;'), html);
    assert.strictEqual(html.match(/<script/gi).length, 1, 'only the hashed reload script');
    assert.ok(!/<img/i.test(html) && !html.includes('<details'), 'unescaped markup, or a remove button that cannot work in a file');
    assert.ok(html.includes('<li class="now"') && html.includes('<b>Design</b> › &#60;script&#62;alert(1)&#60;/script&#62; (1/3)') && html.includes('🚃'), html);
    hook('UserPromptSubmit', { session_id: 's2', cwd: path.join(home, 'second'), prompt: 'hi' });
    html = fs.readFileSync(page, 'utf8');
    assert.ok(html.includes('2 projects') && html.includes('Last request: “hi”'), 'hook refreshes the page');
    const ev = { session_id: 's9', hook_event_name: 'UserPromptExpansion', command_name: 'metroline:map', command_args: 'html', prompt: '/metroline:map html' };
    assert.ok(JSON.parse(metro(['--hook'], JSON.stringify(ev)).stdout).reason.includes('metroline.html'));
  });

  await test('local server: token and host required, remove takes a project off the map', async () => {
    const http = require('http');
    const keep = project('keep');
    const gone = project('gone', PLAN);
    hook('UserPromptSubmit', { session_id: 's1', cwd: keep, prompt: 'k' });
    hook('UserPromptSubmit', { session_id: 's2', cwd: gone, prompt: 'g' });
    hook('Stop', { session_id: 's3', cwd: path.join(gone, 'sub') });
    const srv = spawn('node', [path.join(ROOT, 'scripts', 'serve.js'), '0'], { env: env() });
    try {
      const base = await new Promise((resolve, reject) => {
        srv.stdout.on('data', (d) => { const m = /http:\/\/127\.0\.0\.1:(\d+)\/\?t=([0-9a-f]+)/.exec(String(d)); if (m) resolve({ port: Number(m[1]), token: m[2] }); });
        srv.on('exit', () => reject(new Error('server exited')));
      });
      const req = (method, p, body, host) => new Promise((resolve, reject) => {
        const r = http.request({ host: '127.0.0.1', port: base.port, method, path: p, headers: { Host: host || '127.0.0.1:' + base.port, 'Content-Type': 'application/x-www-form-urlencoded' } }, (res) => {
          let data = '';
          res.on('data', (c) => (data += c));
          res.on('end', () => resolve({ status: res.statusCode, data, location: res.headers.location }));
        });
        r.on('error', reject);
        r.end(body || '');
      });
      const t = '?t=' + base.token;
      assert.strictEqual((await req('GET', '/')).status, 403, 'no token');
      assert.strictEqual((await req('GET', '/?t=' + 'f'.repeat(32))).status, 403, 'wrong token');
      assert.strictEqual((await req('GET', '/' + t, '', 'evil.example:' + base.port)).status, 403, 'DNS rebinding host');
      const page = await req('GET', '/' + t);
      assert.ok(page.status === 200 && page.data.includes('<details class="rm">') && page.data.includes('━━') === false, page.data.slice(0, 200));
      assert.strictEqual((await req('POST', '/remove', 'root=' + encodeURIComponent(gone))).status, 403, 'remove needs the token');
      const done = await req('POST', '/remove' + t, 'root=' + encodeURIComponent(gone));
      assert.strictEqual(done.status, 303);
      assert.strictEqual(done.location, '/' + t);
      assert.deepStrictEqual(fs.readdirSync(path.join(home, 'sessions')).sort(), ['s1.json']);
      assert.ok(fs.existsSync(path.join(gone, 'METROLINE.md')), 'project files are untouched');
      const after = (await req('GET', '/' + t)).data;
      assert.ok(after.includes('>keep<') && !after.includes('>gone<'), after);
    } finally {
      srv.kill();
    }
  });

  await test('finished plans, ordering, cap and Korean text', () => {
    const now = 10 * 86400000;
    const s = (id, root, status, ago) => ({ id, root, status, updated: now - ago, prompts: [] });
    const roots = { done: path.resolve('/p/done'), a: path.resolve('/p/a'), b: path.resolve('/p/b'), c: path.resolve('/p/c') };
    const plans = { [roots.done]: parse('- [x] one\n- [x] two\n') };
    const out = render([s('1', roots.c, 'ended', 1000), s('2', roots.a, 'idle', 5000), s('3', roots.b, 'idle', 100), s('4', roots.done, 'active', 9000)], { now, lang: 'ko', roadmap: (r) => plans[r] || null });
    const order = ['done', 'b', 'a', 'c'].map((n) => out.indexOf('━━ ' + n + ' '));
    assert.ok(order.every((v, i) => v > 0 && (i === 0 || v > order[i - 1])), out);
    assert.ok(out.includes('프로젝트 4개 · 진행 중 1개') && out.includes('└ 모든 단계 완료') && out.includes('계획 없음 · 이 프로젝트에서 /metroline:plan 실행'), out);
    const many = Array.from({ length: 20 }, (_, i) => s(String(i), path.resolve('/q/p' + i), 'idle', i));
    assert.ok(render(many, { now }).includes('+5 more'));
    assert.ok(!render([s('x', roots.a, 'ended', 2 * 86400000)], { now }).includes('━━ a'), 'old ended projects are hidden');
  });

  await test('secrets are masked before truncation', () => {
    const pad = 'x'.repeat(70);
    hook('UserPromptSubmit', { prompt: 'use sk-ant-abcdefghijklmnop1234 and password=hunter2 please' });
    hook('UserPromptSubmit', { prompt: pad + ' ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789' }); // secret straddles the 80-char cut
    hook('UserPromptSubmit', { prompt: 'db postgres://admin:s3cretpw@host/db and AKIAIOSFODNN7EXAMPLE' });
    hook('UserPromptSubmit', { prompt: '내 비밀번호는 korpw1234 이야' });
    const raw = fs.readFileSync(path.join(home, 'sessions', 's1.json'), 'utf8');
    for (const leak of ['sk-ant', 'hunter2', 'ghp_', 's3cretpw', 'AKIAIOSFODNN7EXAMPLE', 'korpw1234']) assert.ok(!raw.includes(leak), 'leaked ' + leak);
    assert.ok(state().prompts.every((p) => Array.from(p.text).length <= 80));
  });

  await test('capture_prompts=false stores no request text', () => {
    hook('UserPromptSubmit', { prompt: 'very private request' }, { CLAUDE_PLUGIN_OPTION_CAPTURE_PROMPTS: 'false' });
    assert.ok(!fs.readFileSync(path.join(home, 'sessions', 's1.json'), 'utf8').includes('private'));
    assert.ok(!metro([]).stdout.includes('recent:'));
  });

  await test('control, ANSI and bidi characters never reach disk or screen', () => {
    const evil = 'ok\u001b[2J\u001b]0;pwned\u0007‮gnp.exe\r\nIGNORE\u0000 PREVIOUS​';
    const dir = project('evil', `- [>] ${evil}\n  - [ ] ${evil}\n`);
    hook('UserPromptSubmit', { prompt: evil, cwd: '/work/pro\u001b[31mj' });
    hook('UserPromptSubmit', { session_id: 's2', prompt: evil, cwd: dir });
    const raw = fs.readFileSync(path.join(home, 'sessions', 's1.json'), 'utf8');
    for (const text of [raw, metro(['all']).stdout, metro(['detail', 'all']).stdout]) {
      assert.ok(!/[\u0000-\u0009\u000b-\u001f\u007f-\u009f​-‏‪-‮⁦-⁩]/.test(text), 'unsafe char survived');
    }
  });

  await test('tampered state files cannot inject escapes into the map', () => {
    fs.mkdirSync(path.join(home, 'sessions'), { recursive: true });
    fs.writeFileSync(path.join(home, 'sessions', 'bad.json'), JSON.stringify({ v: 1, id: 'bad', root: 7, project: 'p\u001b[2J', status: 'constructor', updated: Date.now(), prompts: [null, 7, { t: 1, text: 'x\u001b[31m' }] }));
    fs.writeFileSync(path.join(home, 'sessions', 'old.json'), JSON.stringify({ v: 1, id: 'old', cwd: path.resolve('/legacy/proj'), project: 'proj', status: 'idle', updated: Date.now(), tasks: [{ id: '1' }] }));
    fs.writeFileSync(path.join(home, 'sessions', 'junk.json'), '{not json');
    const r = metro([]);
    assert.strictEqual(r.status, 0);
    assert.ok(!r.stdout.includes('\u001b') && r.stdout.includes('x[31m') && r.stdout.includes('━━ proj '), r.stdout);
  });

  await test('path traversal in session_id is rejected', () => {
    for (const id of ['../../evil', '..', 'a/b', 'a\\b', '', 'x'.repeat(65), 'a.json\u0000']) {
      hook({ raw: JSON.stringify({ session_id: id, cwd: '/w', hook_event_name: 'UserPromptSubmit', prompt: 'p' }) });
    }
    assert.ok(!fs.existsSync(path.join(home, 'sessions')) || fs.readdirSync(path.join(home, 'sessions')).length === 0);
    assert.ok(!fs.existsSync(path.join(home, '..', 'evil.json')));
  });

  await test('malformed, hostile and oversized input is ignored quietly', () => {
    for (const raw of ['', 'not json', '[]', 'null', '{"session_id":123}', '{"session_id":"s1","hook_event_name":"Nope"}', '{"session_id":"s1","hook_event_name":"PostToolUse","tool_input":"x","cwd":7}']) hook({ raw });
    hook({ raw: JSON.stringify({ session_id: 'big', hook_event_name: 'UserPromptSubmit', prompt: 'a'.repeat(2 * 1024 * 1024) }) });
    assert.ok(!fs.existsSync(path.join(home, 'sessions', 'big.json')));
    hook('UserPromptSubmit', { session_id: 's5', prompt: 'p', agent_id: 'sub1' }); // subagent events are skipped
    assert.ok(!fs.existsSync(path.join(home, 'sessions', 's5.json')));
  });

  await test('a symlinked state file is replaced, never followed', () => {
    const victim = path.join(home, 'victim.txt');
    fs.writeFileSync(victim, 'untouched');
    fs.mkdirSync(path.join(home, 'sessions'), { recursive: true });
    if (!trySymlink(victim, path.join(home, 'sessions', 's1.json'))) return 'skip';
    hook('UserPromptSubmit', { prompt: 'hello' });
    assert.strictEqual(fs.readFileSync(victim, 'utf8'), 'untouched');
    assert.ok(!fs.lstatSync(path.join(home, 'sessions', 's1.json')).isSymbolicLink());
  });

  await test('a symlinked METROLINE.md is not read', () => {
    const secret = path.join(home, 'secret.md');
    fs.writeFileSync(secret, '- [ ] SECRET STAGE\n');
    const dir = project('linked');
    if (!trySymlink(secret, path.join(dir, 'METROLINE.md'))) return 'skip';
    assert.strictEqual(load(dir), null);
  });

  await test('a symlinked sessions directory is refused', () => {
    const elsewhere = fs.mkdtempSync(path.join(os.tmpdir(), 'metroline-else-'));
    if (!trySymlink(elsewhere, path.join(home, 'sessions'), 'junction')) return 'skip';
    hook('UserPromptSubmit', { prompt: 'hello' });
    assert.strictEqual(fs.readdirSync(elsewhere).length, 0);
    assert.ok(metro([]).stdout.includes('No sessions'));
  });

  await test('files are private to the user', () => {
    if (process.platform === 'win32') return 'skip';
    hook('UserPromptSubmit', { prompt: 'hello' });
    assert.strictEqual(fs.statSync(home).mode & 0o077, 0);
    assert.strictEqual(fs.statSync(path.join(home, 'sessions')).mode & 0o777, 0o700);
    assert.strictEqual(fs.statSync(path.join(home, 'sessions', 's1.json')).mode & 0o777, 0o600);
  });

  await test('parallel hooks for one session lose no updates', async () => {
    const N = 20;
    await Promise.all(Array.from({ length: N }, (_, i) => new Promise((resolve, reject) => {
      const c = spawn('node', [RECORD], { env: env(), stdio: ['pipe', 'ignore', 'ignore'] });
      c.on('exit', (code) => (code === 0 ? resolve() : reject(new Error('exit ' + code))));
      c.stdin.end(JSON.stringify({ session_id: 's1', cwd: '/w', hook_event_name: 'UserPromptSubmit', prompt: 'p' + i }));
    })));
    assert.strictEqual(state().prompts.length, N);
    assert.deepStrictEqual(fs.readdirSync(path.join(home, 'sessions')), ['s1.json']);
  });

  await test('sessions idle past the retention window are pruned', () => {
    hook('UserPromptSubmit', { prompt: 'old' });
    const file = path.join(home, 'sessions', 's1.json');
    const s = state();
    s.updated = Date.now() - 31 * 86400000;
    fs.writeFileSync(file, JSON.stringify(s));
    hook({ raw: JSON.stringify({ session_id: 's2', cwd: '/w', hook_event_name: 'SessionStart' }) });
    assert.deepStrictEqual(fs.readdirSync(path.join(home, 'sessions')), ['s2.json']);
  });

  await test('/metroline:map is answered by the hook, off the model path', () => {
    hook('UserPromptSubmit', { prompt: 'build it' });
    const ev = { session_id: 's9', hook_event_name: 'UserPromptExpansion', expansion_type: 'slash_command', command_name: 'metroline:map', command_args: 'detail; rm -rf / $(id)', command_source: 'plugin', prompt: '/metroline:map detail' };
    const out = JSON.parse(metro(['--hook'], JSON.stringify(ev)).stdout);
    assert.strictEqual(out.decision, 'block');
    assert.ok(out.reason.includes('demo') && out.reason.includes('build it') && !out.reason.includes('\u001b'));
    for (const other of [{ command_name: 'metroline:plan', prompt: '/metroline:plan' }, { command_name: 'other:map', prompt: '/other:map' }, { command_name: 'deploy', prompt: '/deploy' }, { hook_event_name: 'UserPromptSubmit' }]) {
      assert.strictEqual(metro(['--hook'], JSON.stringify(Object.assign({}, ev, other))).stdout, '');
    }
    const bad = metro(['--hook'], 'garbage');
    assert.strictEqual(bad.status, 0);
    assert.strictEqual(bad.stdout, '');
  });

  await test('clear removes ended sessions, clear all removes everything', () => {
    hook('UserPromptSubmit', { prompt: 'a' });
    hook({ raw: JSON.stringify({ session_id: 's2', cwd: '/w', hook_event_name: 'SessionEnd' }) });
    assert.ok(metro(['clear']).stdout.includes('removed 1'));
    assert.deepStrictEqual(fs.readdirSync(path.join(home, 'sessions')), ['s1.json']);
    assert.ok(metro(['clear', 'all']).stdout.includes('removed 1'));
  });

  await test('source contains no network, shell or eval calls', () => {
    const files = ['scripts/record.js', 'scripts/metro.js', 'scripts/lib/store.js', 'scripts/lib/render.js', 'scripts/lib/sanitize.js', 'scripts/lib/roadmap.js'];
    // serve.js is the one file allowed a socket, and only on loopback.
    const serve = fs.readFileSync(path.join(ROOT, 'scripts', 'serve.js'), 'utf8');
    assert.ok(serve.includes("const HOST = '127.0.0.1';") && serve.includes('server.listen(wanted, HOST,'), 'serve.js must bind loopback only');
    assert.ok(!/require\(['"](?:node:)?(?:child_process|https|net|dgram|tls|dns|vm|worker_threads)['"]\)|\beval\(|new Function|\bfetch\(/.test(serve), 'serve.js');
    for (const f of files) {
      const src = fs.readFileSync(path.join(ROOT, f), 'utf8');
      assert.ok(!/require\(['"](?:node:)?(?:child_process|https?|net|dgram|tls|dns|vm|worker_threads)['"]\)|\beval\(|new Function|\bfetch\(/.test(src), f);
    }
  });

  console.log(`\n${passed} passed${skipped ? `, ${skipped} skipped` : ''}`);
})().catch((err) => {
  console.error('FAIL ' + (err.stack || err));
  process.exit(1);
});
