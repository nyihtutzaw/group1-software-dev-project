# Project documents

ITCS514 Software Project Management · Group 1 · Term 1, 2026/27.
Client (case study): Julian Ferris, Head of Registry Integrity.

| File | What it is |
|---|---|
| [CRVR-Project-Design-Report-v0.1.pdf](CRVR-Project-Design-Report-v0.1.pdf) | Problem, benefits, the five features, platform, UI design, team responsibilities |
| [CRVR-Mock-UI-v0.1.html](CRVR-Mock-UI-v0.1.html) | Interactive UI mock-up — open in a browser; the UI source of truth |
| [CRVR-Project-Charter-v2.00.docx](CRVR-Project-Charter-v2.00.docx) | Project charter: objectives, functional requirements FR-01…FR-11, scope |
| [CRVR-WBS.xlsx](CRVR-WBS.xlsx) | Work breakdown structure (satellite monitoring and inter-registry hook marked deferred) |
| [CRVR-Gantt.xlsx](CRVR-Gantt.xlsx) | Schedule baseline and critical path |
| [CRVR-Architecture.png](CRVR-Architecture.png) | Architecture diagram |

## Requirements at a glance

| Req | Requirement | Built in |
|---|---|---|
| FR-01 | Project registration | F1 |
| FR-02 | Evidence submission (write-once) | F1 |
| FR-03 | Geospatial boundary management | F2 |
| FR-04 | Geographic overlap detection | F2 |
| FR-05 | Satellite monitoring | **Deferred** |
| §5.3 | Structured verification workflow | F3 |
| FR-07 | Immutable audit & verification history | F5 (+ F3) |
| FR-08 | Buyer access | F4 |
| FR-09 | Audit logging | F5 |
| FR-10 | User & role management, separation of duties (maker-checker) | F5 (+ F3) |
| FR-11 | Inter-registry flagging hook | **Deferred** |

Out of scope (charter): replacing physical site verification, automated additionality decisions,
migration of existing projects, cross-registry reconciliation, advanced internal dashboards, full
workflow automation, blockchain.
