# Features

Five features make up the web application we build this term. Each has one owner who builds it end
to end (data model, API, UI, tests) and keeps its context doc current.

| Feature | Owner | Supports | Issue | Doc |
|---|---|---|---|---|
| F1 Project registration & evidence | Jingqing | Zay Yar Phyo, Nyi Htut Zaw | [#3](https://github.com/nyihtutzaw/group1-software-dev-project/issues/3) | [F1-registration.md](F1-registration.md) |
| F2 Geospatial boundary & overlap detection | Nyi Htut Zaw | Pyae Phyo Hein | [#4](https://github.com/nyihtutzaw/group1-software-dev-project/issues/4) | [F2-boundary.md](F2-boundary.md) |
| F3 Verification workflow | Pyae Phyo Hein | Jingqing | [#5](https://github.com/nyihtutzaw/group1-software-dev-project/issues/5) | [F3-verification.md](F3-verification.md) |
| F4 Public registry & buyer transparency | Zay Yar Phyo | — | [#6](https://github.com/nyihtutzaw/group1-software-dev-project/issues/6) | [F4-registry.md](F4-registry.md) |
| F5 Security & auditability | Put Thitisawat | Nyi Htut Zaw (CI/CD) | [#7](https://github.com/nyihtutzaw/group1-software-dev-project/issues/7) | [F5-security-audit.md](F5-security-audit.md) |

Cross-cutting work: shared UI kit and responsive layout (Zay Yar Phyo), PostGIS schema and spatial
queries (Nyi Htut Zaw), Docker / GitHub Actions / Cloud Run (Put Thitisawat, Nyi Htut Zaw).

## Suggested build order

The app shell (layout, sign-in, roles, menus, placeholder pages) is already done. Features can start
in parallel; these are the hand-offs to agree early:

1. **F1 project model** — F2, F3 and F4 all reference a project. Agree the `projects` table first.
2. **F5 `record_action()`** — every feature writes critical actions to the ledger through it.
   Agree the function signature early; F5 can ship a stub and fill it in later.
3. **F2 overlap result** — F1 (registration step) and F3 (checklist) display it.
4. **F3 approval** — F4 only lists credits from approved projects.

## Deferred — designed, not built this term

Do **not** implement these; the design keeps room for them.

- **Satellite monitoring (FR-05, WBS 6.0).** Continuous land-cover change detection. Needs a
  commercial imagery subscription we cannot procure. The home dashboard keeps a monitoring-alert
  slot and the registry traceability panel a "Monitoring" row — show them as placeholders.
- **Inter-registry flagging hook (FR-11, WBS 9.4).** An endpoint for future duplicate checks
  against other registries. No external registry to build against.
