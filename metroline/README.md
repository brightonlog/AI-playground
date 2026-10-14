# Metroline

A subway map of your projects across parallel Claude Code sessions.

Run several sessions on several projects and you lose track of which project is where. Metroline draws each project as a line and each stage of the project as a station. All sessions of one project, including sessions started in its subfolders, share one line.

```
METROLINE  2 projects · 1 running

━━ music-game   ▶ running · 2m ago · 2 sessions
   Plan ●━━ Design ◉── Build ○── Test ○── Deploy ○
   └ Design: API spec (1/3)

━━ ai_office   ‖ waiting for you · 1h ago
   no plan · run /metroline:plan in this project
   recent: “connect the calendar API”
```

`●` done, `◉` in progress, `○` not started. Heavy track `━━` lies behind you, thin track `──` ahead. The `└` line names the current stage, its current task, and how many of its tasks are done.

## Install

```
/plugin marketplace add <your-github-user>/metroline
/plugin install metroline@metroline-marketplace
```

Requires Node.js 18+ on `PATH`. No other dependencies.

Install at user scope (the default). Every session in every folder is then recorded automatically.

## Stages: `METROLINE.md`

Each project keeps its stages in `METROLINE.md` at the project root. Run `/metroline:plan` in the project to have Claude create or update it, or write it yourself:

```markdown
- [x] Plan
- [>] Design
  - [x] DB schema
  - [>] API spec
  - [ ] ERD
- [ ] Build
```

| Rule | |
|---|---|
| Unindented checklist item | a stage |
| Indented item | a task of the stage above |
| Any other line | ignored |
| `[x]` | done |
| `[>]` `[~]` `[/]` | in progress |
| `[ ]` | not started; a stage with tasks is done when all are done, in progress when any has started |
| Limits | 12 stages, 30 tasks per stage, 60 chars per item, 64 KB per file |

The viewer re-reads the file only when its modification time changes.

When a session starts in a project without `METROLINE.md`, a one-line note suggests `/metroline:plan`. Only you see it; Claude does not. Turn it off with the `plan_reminder` option in `/plugin`.

The project root is `CLAUDE_PROJECT_DIR` (or the session's working folder), moved up to the nearest folder that holds `METROLINE.md` or `.git`. Your home folder never counts as a project root.

## Use

| Where | Command |
|---|---|
| Inside a session | `/metroline:map` · `/metroline:map detail` · `/metroline:map all` |
| Browser | `/metroline:map html` once, then open the printed `file:///` link |
| Browser, with remove buttons | `node "$(cat ~/.metroline/root)/scripts/serve.js"`, then open the printed link |
| Any terminal | `node "$(cat ~/.metroline/root)/scripts/metro.js" watch` |

Suggested alias: `alias metro='node "$(cat ~/.metroline/root)/scripts/metro.js"'`, then `metro watch` in a spare pane.

| Word | Effect |
|---|---|
| `detail` | list every stage and task |
| `all` | include ended projects and lift the 15-line cap |
| `watch` | redraw every 2 s (terminal only) |
| `html` | write `~/.metroline/metroline.html` and print its link; from then on every hook event rewrites it, and the open page reloads every 5 s |
| `clear` / `clear all` | delete ended sessions / delete everything |

Lines are sorted running, then waiting, then ended; most recent first within each. Text is Korean when `LANG` starts with `ko` (override with `METROLINE_LANG`), English otherwise.

`/metroline:map` is answered by a hook before the prompt reaches the model. It costs no tokens. Claude Code labels the output "blocked by hook"; that label is expected.

## Privacy and security

Everything stays on your machine. The code makes no outbound network calls, spawns no processes, and has no dependencies. It is plain, unbundled JavaScript; read it in `scripts/`.

| Stored in `~/.metroline/sessions/<session-id>.json` | Limit |
|---|---|
| Session id, project root path, session title | |
| First 80 chars of each request | last 30 requests; off with the `capture_prompts` option |

Set `METROLINE_HOME` to keep the data somewhere else.

| Risk | Control |
|---|---|
| Secrets pasted into a prompt | API keys, tokens, JWTs, private keys, `password=…`, URL credentials are masked before truncation |
| Other local users reading state | directory `0700`, files `0600` |
| Text from one project steering Claude in another | the map is shown to you only; no hook writes to model context and no tool lets Claude read the state |
| Other websites using the local server | it listens on 127.0.0.1 only; every request needs a random per-run token, and the Host header must be 127.0.0.1 or localhost (blocks DNS rebinding) |
| Script injection in the HTML view | all text is HTML-escaped; the page has no scripts and its CSP blocks scripts and every external request |
| Terminal escape injection | control, ANSI, zero-width and bidi characters are stripped on write and again on display, `METROLINE.md` included |
| Path traversal, symlink tricks | session ids are pattern-checked; writes use exclusive temp files plus rename; symlinked directories and a symlinked `METROLINE.md` are refused |
| Command injection | hook input is only parsed as JSON; arguments are matched against a fixed word list |
| A failing hook stalling your session | hooks print nothing (except the user-only plan note), always exit 0, and time out after 5 s |
| Data piling up | sessions idle for 30 days are deleted |

Masking is pattern-based and cannot recognise every secret. If your prompts often contain sensitive text, turn `capture_prompts` off.

To remove all data: `/metroline:map clear all`, or delete `~/.metroline`. Uninstalling the plugin does not delete that folder.

Removing a project in the browser deletes only its session records in `~/.metroline`. The project folder and its `METROLINE.md` are untouched. New work in that project brings the line back.

## Limits

- Claude Code only (terminal, and wherever Claude Code hooks run). Chats in the Claude desktop or web app have no hooks and do not appear.
- A session killed without a clean exit shows as running for up to 2 hours, then as waiting.
- Stages move only when `METROLINE.md` changes. Ask Claude to update it, or run `/metroline:plan` again.

## Develop

```
node test/run.js               # no dependencies; symlink tests skip where symlinks are not allowed
claude plugin validate .
claude --plugin-dir .          # try it without installing
```

## License

MIT
