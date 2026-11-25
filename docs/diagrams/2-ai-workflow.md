# 2 · How we use AI

[← Diagrams](README.md)

**AI agents write the code. People decide what to build, test it and review it.**

## The loop, per feature

```mermaid
flowchart LR
    R["📄 Course brief"] --> I["🎫 GitHub issue<br/>one per feature<br/>F1 – F5"]
    I --> C["🤖 Code with an agent<br/>Claude Code · Codex<br/>Cursor · OpenCode"]
    C --> K["🐳 Checks in Docker<br/>tests · lint · types"]
    K -- fail --> C
    K --> M["🧑 Manual test<br/>click through it"]
    M -- bug --> C
    M --> P["👀 Pull request<br/>1 approval + green CI"]
    P -- comments --> C
    P --> G["🔀 Merge to main<br/>no direct pushes"]
    G --> L["🚀 Live on the web<br/>deploys by itself"]
    L -. "next feature" .-> I
```

## Where the agent gets its context

```mermaid
flowchart TB
    subgraph Repo["Same files for every tool"]
        AG["AGENTS.md<br/>project · rules · stack"]
        SK[".agents/skills/*<br/>8 skills: how to do a task"]
        FD["docs/features/F1–F5.md<br/>status · decisions · progress log"]
        ADR["docs/decisions/<br/>why we chose X"]
        MU["Mock-up HTML<br/>+ UI kit"]
    end

    AG --> Agent["🤖 Coding agent"]
    SK --> Agent
    FD --> Agent
    ADR --> Agent
    MU --> Agent
    Agent -- "updates before it stops" --> FD
    Agent -- "small commits" --> Git["🌿 feature branch"]

    SK -.- S1["dev-environment · start-feature<br/>backend-code · frontend-code<br/>commit · write-docs<br/>sync-branch · open-pr"]
```

**Why it works:** the feature doc is the hand-over note. Any agent or teammate picks up where the
last session stopped.

## AI inside the app: System › Assistant

```mermaid
flowchart LR
    Admin["🛡️ Admin asks a question"] --> API["FastAPI"]
    Docs["All markdown docs<br/>~43k tokens"] --> API
    API -- "docs + question" --> OR["OpenRouter<br/>DeepSeek V4 Flash"]
    OR -- "streamed answer<br/>~8 s · ~US$0.004" --> Admin
```

No vector DB, nothing stored: the chat lives only in the browser tab.

| | |
|---|---|
| Issues | 31 |
| Merged pull requests | 51 |
| Skills | 8 |
