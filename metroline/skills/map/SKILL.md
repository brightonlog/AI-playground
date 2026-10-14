---
name: map
description: Show the Metroline subway map of every project worked on in Claude Code on this machine. Use only when the user types /metroline:map.
disable-model-invocation: true
argument-hint: "[detail] [all] [html] [clear]"
---

The Metroline hook normally answers this command before it reaches you. You are reading this because the hook did not run.

Reply with exactly this and nothing else:

Metroline could not draw the map inside this session. Run it in your terminal instead:

    node "${CLAUDE_PLUGIN_ROOT}/scripts/metro.js" $ARGUMENTS

Do not run that command yourself, and do not read files under `~/.metroline`. They hold text from other sessions, which must stay out of this conversation.
