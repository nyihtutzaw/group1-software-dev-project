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

**In review** — all seven acceptance criteria built on `feature/F2-boundary-overlap` (PR closes #4).
Developers draw (pen tool, phone-friendly) or upload a boundary, see the overlap check live, and
save it; overlaps above 0.5% are flagged and block issuance until registry staff resolve them.

## Scope

Boundaries are captured by uploading a GPS/geospatial file or drawing the polygon on a map —
including on a phone in the field. Each is stored as geographic data and screened against every
registered boundary. An intersection names the conflicting project, shows the overlapping area,
and **blocks issuance** until resolved. This is the client's highest priority: it is the control
against double-selling, and nothing like it exists today.

**Out of scope:** satellite monitoring of boundaries (deferred).

## Acceptance criteria

From WBS 5.x and the design report — all done:

1. ✅ Spatial schema with a standard CRS: `boundaries.geom` MULTIPOLYGON SRID 4326, GiST index (5.1.1).
2. ✅ Stored as validated geometry; area **computed** by PostGIS on the geography, never claimed (5.1.2).
3. ✅ GeoJSON, KML/KMZ and zipped shapefile imports, validated; non-WGS 84 rejected (5.1.3).
4. ✅ Phone drawing: pen tool, tap corners, drag to adjust; map fills the width at 420 px (5.2.1).
5. ✅ Overlaps detected across all registered projects with a 0.5% tolerance (5.3.1).
6. ✅ Overlaps above tolerance are flagged and block issuance until resolved — `issuance_blocked()` (5.3.2).
7. ✅ Result shows conflicting project (code, name, registration date), overlap ha and % of area.

## Decisions

- 2026-10-27 — Overlap check runs in PostGIS (`ST_Intersects` / `ST_Intersection` / `ST_Area` on
  geography), not in Python (design report, platform section).
- 2026-10-28 — Tolerance 0.5% of the **new** project's area (mock-up), setting
  `OVERLAP_TOLERANCE_PCT`. Compared at the 2 decimals shown, so exactly "0.50%" never blocks.
  Overlaps within tolerance are reported but not flagged; touching edges are not overlaps.
- 2026-10-28 — One current boundary per project; redrawing replaces it and marks the old open or
  disputed flags `superseded` (history kept, fresh screening wins).
- 2026-10-28 — The **later** registration is the one flagged — the earlier project is not touched.
- 2026-10-28 — Flag lifecycle `open → disputed → resolved` (+ `superseded`). The project's developer
  disputes; registry staff/admin resolve; nobody resolves a flag on their own project (FR-10).
  Open and disputed flags block issuance.
- 2026-10-28 — Saving a boundary that overlaps is allowed (it is flagged); the *submission* (F1) and
  *issuance* (F3/F4) are what get blocked — they must call `issuance_blocked(db, project_id)`.
- 2026-10-28 — Map: Leaflet 1.9 + Geoman (free) with OpenStreetMap tiles; no API key. The page is
  lazy-loaded so map code (~120 KB gzipped) is not in the main bundle.
- 2026-10-28 — Import parsing on the server (one validation path): pyshp for shapefiles,
  defusedxml for KML; max 5 MB upload, 50 MB unzipped, 10,000 vertices.
- 2026-10-28 — F1 `projects` did not exist yet, so F2 added a **minimal stub** in F1's folder
  (id, code, name, owner, status) and seeded demo projects; Jinkin extends it. F5's ledger did not
  exist, so F2 added a `record_action()` **stub** (logs only) as the call site; Put fills it in.

## API

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/api/boundaries` | developer, verifier, registry_staff, admin | All registered boundaries as GeoJSON FeatureCollection (code, name, area_ha, flagged) |
| POST | `/api/boundaries/check` | developer, verifier, registry_staff, admin | Validate + screen a geometry without saving `{geometry, project_id?}` → area, vertices, overlaps, blocked |
| POST | `/api/boundaries/import` | developer, admin | Multipart `file` (GeoJSON/KML/KMZ/zip shapefile) → `{filename, geometry}`; nothing saved |
| GET | `/api/boundaries/{project_id}` | developer (own), verifier, registry_staff, admin | Saved boundary + live check + flags + `issuance_blocked` + `can_edit`; 404 if none |
| PUT | `/api/boundaries/{project_id}` | developer (own), admin | Save/replace `{geometry, source: drawn\|uploaded}`; flags overlaps above tolerance |
| POST | `/api/boundaries/flags/{id}/dispute` | developer (own project), admin | `{reason ≥ 10 chars}` open → disputed |
| POST | `/api/boundaries/flags/{id}/resolve` | registry_staff, admin (not on own project) | `{note ≥ 5 chars}` open/disputed → resolved |

Ledger actions written via `record_action()`: `boundary.saved`, `boundary.overlap_detected`
(actor = system), `boundary.overlap_disputed`, `boundary.overlap_resolved`.

**For other features:** `from app.features.boundary.service import issuance_blocked` →
`issuance_blocked(db, project_id)` returns a reason string or `None`.

## Pages

| Route | Roles | Shows |
|---|---|---|
| `/boundary?project=<id>` | developer, verifier, registry_staff, admin | Map (draw/edit/upload for owner + admin), live overlap alert, key figures, overlap flags with dispute/resolve |

Deep link from F1/F3: `/boundary?project=<id>`.

## Data model

| Table | Key columns | Notes |
|---|---|---|
| `boundaries` | project_id (unique FK), geom MULTIPOLYGON 4326 (GiST), area_m2, source, updated_by_id, updated_at | one current boundary per project |
| `overlap_flags` | project_id, other_project_id, overlap_m2, overlap_pct, status, dispute_reason, resolution_note, resolved_by_id, resolved_at | status `open\|disputed\|resolved\|superseded` |

Migrations: `…_add_projects_table_f1_stub.py`, `…_add_boundaries_and_overlap_flags_f2.py`.

## Depends on / used by

- Uses: F1 `projects` (stub for now), F5 `record_action()` (stub for now), auth roles.
- Used by: F1 (inline overlap banner + block submission via `issuance_blocked`), F3 (checklist item
  "Boundary has no overlap" — call `issuance_blocked` / `GET /api/boundaries/{id}`), F4 (issuance gate).

## Open questions

- Should a resolved overlap be re-flagged if the developer later redraws and the overlap grows?
  (Today: any redraw re-screens and re-flags above tolerance.)
- Tolerance registry-wide (current) or per methodology?
- `projects` shape: agree the stub's columns with Jinkin (F1) before F1 adds its fields.

## Progress log

### 2026-10-28 · feature/F2-boundary-overlap
- Goal: the whole of F2 (issue #4) on one branch, one PR.
- Plan:
  1. Minimal `projects` stub in F1's folder (id, code, name, owner, status) so boundaries have
     something to belong to — Jinkin extends it later.
  2. `record_action()` stub in F5's folder as the ledger call site — Put replaces the body later.
  3. `boundaries` + `overlap_flags` tables and migration.
  4. Service: validate geometry and compute area in PostGIS; find overlaps with tolerance.
  5. Import GeoJSON, KML and zipped shapefiles.
  6. API: check, save, list, get, dispute, resolve; `issuance_blocked()` for F3/F4.
  7. Demo projects and boundaries reproducing the mock-up (CRVR-0147 overlapping CRVR-0092).
  8. Map page: Leaflet + Geoman draw/edit, file upload, overlap alert and summary, phone-first.
  9. Update this doc (API, data model, decisions) and open the PR.
- Done (2026-10-28): projects stub, record_action stub, boundaries + overlap_flags tables,
  PostGIS validation/area/overlap service, GeoJSON/KML/KMZ/shapefile import, API with dispute and
  resolve, demo data reproducing the mock-up, Leaflet + Geoman map page (desktop and phone).
  Tests: 56 new backend tests (geometry, import, API), 7 new frontend tests; end-to-end check in a
  real browser (draw → check → save, dispute → resolve).
- Next: F1/F3/F4 call `issuance_blocked()`; F5 replaces the `record_action()` stub.
