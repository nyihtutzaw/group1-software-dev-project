# 0011 — A project assistant that answers from the docs, through OpenRouter

**Date:** 2026-11-20 · **Status:** Accepted

## Context

Admins (the team, and the professor testing the hosted demo) ask the same questions about CRVR again
and again: what a feature does, why something was built a certain way, how the demo is deployed. The
answers are already in the repository's markdown docs, but those are spread over 26 files. We
wanted a *System › Assistant* page that answers such questions, kept cheap (a school project paid
from a team member's account) and without storing conversations.

## Decision

- **Knowledge = the markdown docs, all of them, on every question.** `README.md`, `AGENTS.md` and
  `docs/**/*.md` (except the feature-doc template) are about 168 kB / 43k tokens. They go to the
  model as the system prompt with each question. No embeddings or vector search: nothing to build or
  keep in sync, and the model sees the whole picture. The docs ship with the image
  (`/knowledge`, `ASSISTANT_DOCS_DIR`), so answers match the deployed version.
- **Model via OpenRouter, `deepseek/deepseek-v4-flash`, reasoning off.** Measured on 2026-11-20:
  ~8 s and ~US$0.004 a question. With reasoning on it took over 30 s and ran out of answer tokens;
  Gemini 3 Flash answered as well but cost ~6×. The model is a setting (`OPENROUTER_MODEL`).
- **Stateless.** The browser keeps the chat in `sessionStorage` (per user, gone when the tab
  closes or on *Clear chat*) and sends the latest 12 messages with each question. The server
  stores nothing: no table, no ledger entry, no log of the text.
- **Admin only**, 20 questions a minute per admin (in memory; one Cloud Run instance), answer
  capped at 2,000 tokens and streamed as plain text.
- **No new dependency:** the OpenRouter call uses Python's `urllib`; the page renders Markdown with
  a small in-house renderer (React elements only, no HTML injection).
- The key is a secret: `backend/.env` locally, Secret Manager `crvr-openrouter-api-key` on Cloud
  Run. The OpenRouter key itself has a spending limit.

## Consequences

- Answers are only as good as the docs: keeping the feature docs current now also keeps the
  assistant right. Answers can still be wrong; the page says so and each answer names its source.
- If the docs grow past a few hundred kB, cost and latency grow with them; then pick relevant
  files per question (or cache the prompt) instead of sending everything.
- Questions leave our infrastructure for OpenRouter and the model provider: never put real
  personal data or secrets in the docs (already a rule) or in a question.
- Deploys need the `crvr-openrouter-api-key` secret to exist; without a key locally, the page
  just says the assistant is not set up.
