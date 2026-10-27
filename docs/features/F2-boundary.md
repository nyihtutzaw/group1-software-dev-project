# F2 — Geospatial boundary & overlap detection

> Context doc for people and AI agents. Read before working on this feature; update before you stop.
> How: `.agents/skills/write-docs/SKILL.md`.

| | |
|---|---|
| **Owner** | Nyi Htut Zaw (supports: Pyae Phyo Hein) |
| **Issue** | [#4](https://github.com/nyihtutzaw/group1-software-dev-project/issues/4) — requirements and acceptance checklist |
| **Requirements** | FR-03 Geospatial boundary management · FR-04 Overlap detection · WBS 5.0 |
| **Code** | `backend/app/features/boundary/` · `frontend/src/features/boundary/` |
| **Mock-up** | *Map* (Boundary) — desktop and 420 px phone |

## Status

Not started — placeholder page at `/boundary`; `GET /api/boundaries` returns `[]`.

## Scope

Boundaries are captured by uploading a GPS/geospatial file or drawing the polygon on a map —
including on a phone in the field. Each is stored as geographic data and screened against every
registered boundary. An intersection names the conflicting project, shows the overlapping area,
and **blocks issuance** until resolved. This is the client's highest priority: it is the control
against double-selling, and nothing like it exists today.

**Out of scope:** satellite monitoring of boundaries (deferred).

## Acceptance criteria

From WBS 5.x and the design report:

1. Spatial schema deployed with a standard CRS (WGS 84, SRID 4326) (5.1.1).
2. A boundary is stored as validated geometry; its area is **computed**, not claimed (5.1.2).
3. GeoJSON, KML and shapefile imports are accepted and validated (5.1.3).
4. A non-technical user can draw a boundary on a phone (5.2.1).
5. Overlaps are detected across all registered projects, with a GPS-error tolerance (5.3.1).
6. Flagged overlaps block credit issuance until investigated (5.3.2).
7. The overlap result shows the conflicting project, overlap area and % of the new project's area.

## Decisions

- 2026-10-27 — Overlap check runs in PostGIS (`ST_Intersects` / `ST_Intersection` / `ST_Area` on
  geography), not in Python (design report, platform section).
- 2026-10-27 — Tolerance shown in the mock-up: 0.5% of the project's area. Confirm before building.
- 2026-10-27 — Map library not chosen yet; Leaflet + Geoman (draw/edit polygons, OpenStreetMap
  tiles, no API key) is the default proposal.

## API

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/api/boundaries` | developer, verifier, registry_staff, admin | List boundaries (placeholder) |

## Pages

| Route | Roles | Shows |
|---|---|---|
| `/boundary` | developer, verifier, registry_staff, admin | Boundary map + overlap result — placeholder |

## Data model

| Table | Key columns | Notes |
|---|---|---|
| — | | `boundaries` (project_id, geom MULTIPOLYGON 4326, area_m2) to be designed |

## Depends on / used by

- Uses: F1 `projects`, F5 ledger (boundary change, overlap detected).
- Used by: F1 (inline overlap banner), F3 (checklist item "Boundary has no overlap").

## Open questions

- What happens on "Dispute overlap" — who resolves it, and how?
- Is the tolerance per project or a registry-wide setting?

## Progress log
