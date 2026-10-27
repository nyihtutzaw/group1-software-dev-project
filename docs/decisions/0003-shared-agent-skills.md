# 0003 — One set of agent skills for every AI tool

**Date:** 2026-10-27 · **Status:** Accepted

## Context

Team members use Claude Code, Codex, Cursor and OpenCode. Each tool looks for instructions in a
different place. Separate copies per tool would drift apart.

## Decision

- `AGENTS.md` holds project context and rules (read natively by Codex, Cursor and OpenCode;
  `CLAUDE.md` imports it for Claude Code).
- Skills live once, in `.agents/skills/<name>/SKILL.md` (Agent Skills format: front matter with
  `name` and `description`, then markdown).
- `scripts/sync-agent-skills.sh` writes small stubs to `.claude/skills/` and `.cursor/skills/` that
  point to the real file. Stubs rather than symlinks so Windows checkouts work.
- CI runs the script with `--check`, so stale stubs fail the build.

## Consequences

- Edit a skill in one place; every tool follows the same workflow.
- Adding a tool = adding its folder to `TARGETS` in the script.
- See `docs/agents.md`.
