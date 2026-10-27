@AGENTS.md

## Claude Code notes

- Skills are available as `/dev-environment`, `/start-feature`, `/commit`, … (stubs in
  `.claude/skills/` that point to `.agents/skills/`). Edit the files in `.agents/skills/`, then run
  `sh scripts/sync-agent-skills.sh`.
- Optional permission presets for routine git/docker commands: see `docs/agents.md`.
