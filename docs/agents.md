# Working with AI coding agents

The team uses Claude Code, Codex, Cursor and OpenCode. They all get the same instructions from the
same files, so it doesn't matter which tool a teammate uses.

## How it is wired

```
AGENTS.md                      project context + rules + skill list   ← Codex, Cursor, OpenCode read this
CLAUDE.md                      imports AGENTS.md                      ← Claude Code reads this
.agents/skills/<name>/SKILL.md the skills — the only place to edit them ← Codex, OpenCode read these
.claude/skills/<name>/SKILL.md generated stub → points to .agents/…    ← Claude Code (/commit, …)
.cursor/skills/<name>/SKILL.md generated stub → points to .agents/…    ← Cursor
.cursor/rules/project.mdc      always-on Cursor rule → AGENTS.md
```

Even a tool with no skills support works: `AGENTS.md` lists every skill and tells the agent to read
the SKILL.md for the task.

## Skills

| Skill | What it covers |
|---|---|
| `dev-environment` | Docker commands, checks, adding dependencies, DB reset, troubleshooting |
| `start-feature` | Branch naming, reading context, planning in the feature doc, first commit |
| `backend-code` | FastAPI feature modules, models, PostGIS, migrations, role checks, tests |
| `frontend-code` | Mock-up → UI kit mapping, tokens, routes/nav, data fetching, tests |
| `commit` | Checks, staging, Conventional Commits with feature scope |
| `write-docs` | Feature context docs, decision records, progress log |
| `sync-branch` | Rebasing on main, conflicts, Alembic heads, force-with-lease |
| `open-pr` | PR checklist, gh CLI, template, cleanup after merge |

## Changing a skill

1. Edit `.agents/skills/<name>/SKILL.md` (or add a new folder with a `SKILL.md` that has `name:`
   and a one-line `description:` in its front matter).
2. Run `sh scripts/sync-agent-skills.sh` to regenerate the Claude Code and Cursor stubs.
3. If you added a skill, add a row to the skills table in `AGENTS.md` and above.
4. Commit on a `chore/` or `docs/` branch: `chore(agents): …`. CI fails if the stubs are stale.

A tool that wants skills in another folder: add that folder to `TARGETS` in the script.

## Typical session

```
You:   start F2 — the boundary model and migration
Agent: start-feature → branch feature/F2-boundary-model, reads docs/features/F2-boundary.md,
       writes the plan in the progress log, commits "docs(F2): plan boundary model", pushes
Agent: backend-code → model + migration + tests → commit "feat(F2): …" → next step → commit …
Agent: write-docs → updates Status/API/Progress log → commit
You:   open a PR
Agent: sync-branch → open-pr
```

## No AI attribution

Commits and PRs carry no AI attribution (no `Co-Authored-By:` trailers, no "Generated with …"
lines). The skills tell every agent this, but some tools add a trailer by default, so also switch it
off in your tool:

- **Claude Code:** in `.claude/settings.local.json` or `~/.claude/settings.json`, set
  `"includeCoAuthoredBy": false` (newer versions: `"attribution": { "commit": "", "pr": "" }`).
- **Cursor, Codex, OpenCode:** turn off any commit co-author / attribution option in the tool's
  settings if it has one.

## Optional: fewer permission prompts in Claude Code

Claude Code asks before running shell commands. To pre-approve the routine ones for this repo,
create `.claude/settings.local.json` (personal, git-ignored) — or, if the team agrees,
`.claude/settings.json` (shared) — with:

```json
{
  "permissions": {
    "allow": [
      "Bash(docker compose:*)",
      "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git branch:*)",
      "Bash(git switch:*)", "Bash(git add:*)", "Bash(git commit:*)", "Bash(git fetch:*)",
      "Bash(git pull:*)", "Bash(git push:*)", "Bash(git rebase:*)", "Bash(gh pr:*)"
    ],
    "deny": ["Bash(git push --force:*)", "Bash(git push -f:*)", "Read(./.env)"]
  }
}
```

Other tools have equivalents (Codex `approval_policy`, Cursor's command allow-list, OpenCode
`permission` config) — set them in your personal config.
