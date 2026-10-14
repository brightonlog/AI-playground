---
name: plan
description: Create or update METROLINE.md, the stage checklist Metroline draws as this project's subway line. Use when the user runs /metroline:plan or asks to set up or update the project's Metroline stages.
argument-hint: "[stages or notes]"
---

Create or update `METROLINE.md` for this project. Metroline reads it to draw the project's line: each stage is a station.

## Where the file goes

1. If `METROLINE.md` exists in the current folder or any parent folder, use that file.
2. Otherwise create it at the top of the git repository (`git rev-parse --show-toplevel`).
3. Outside a git repository, create it in the folder this session was started in.

## Format

```markdown
# Roadmap

- [x] Plan
- [>] Design
  - [x] DB schema
  - [>] API spec
  - [ ] ERD
- [ ] Build
- [ ] Test
- [ ] Deploy
```

- An unindented checklist item is a stage. An indented item is a task of the stage above it. Other lines are ignored.
- `[x]` done, `[>]` in progress, `[ ]` not started.
- Leave a stage `[ ]` if it has tasks: its state is worked out from them.
- Limits: 12 stages, 30 tasks per stage, 60 characters per item. Keep stage names short (one or two words) so the line fits a terminal.

## Steps

1. If the file exists, read it. Keep the user's stage names and order. Change only what the command arguments ($ARGUMENTS) ask for, or the states that the work in this session and the code clearly show have changed.
2. If creating it, take stages from the command arguments ($ARGUMENTS) when given. Otherwise propose 4 to 6 stages that fit this project, based on its README and code, and write them in the user's language. Add tasks only for the stage in progress.
3. Mark states honestly. When unsure, leave an item `[ ]`.
4. Never write secrets, credentials or personal data into the file.
5. Reply with one line naming the current stage, then suggest `/metroline:map` to see the line.
