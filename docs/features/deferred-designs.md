# Deferred features — designs

> Designed, **not built** this term (see [README](README.md#deferred--designed-not-built-this-term)).
> The design report and WBS 6.0 / 9.4.1 say both are designed so they can be added later without
> rework; this file is that design. Do not implement it without a change request to the sponsor.

## FR-05 · Satellite monitoring (WBS 6.0)

Continuous land-cover change detection against each registered boundary after approval. Blocked
by a commercial imagery subscription the team cannot procure (WBS 3.1.1).

### What already reserves its place

| Where | Today |
|---|---|
| Developer Home (`/`) | Monitoring-alert slot, shown as a placeholder |
| Credit page (`/registry/:id`) | "Monitoring" row: *Not available — monitoring is deferred* |
| `GET /api/registry/credits/{id}` | `monitoring: "not_available"` (a `Literal`, so adding values is additive) |
| Buffer pool (F3, #42) | Non-tradable `buffer` batches exist to cover a confirmed reversal |

### Data model

Two tables in a new `backend/app/features/monitoring/` package. Observations are facts from the
provider and are append-only (same trigger pattern as `evidence_files`); alerts carry a workflow.

| Table | Key columns | Notes |
|---|---|---|
| `monitoring_observations` | project_id FK, observed_at, provider, scene_id, canopy_cover_pct, baseline_canopy_pct, change_pct, cloud_cover_pct, imagery_sha256, created_at | One row per scene clipped to the boundary (WBS 6.1.2). The first usable scene after approval sets the baseline (6.2.1). Write-once |
| `monitoring_alerts` | project_id FK, observation_id FK, kind (`canopy_loss`), change_pct, status (`open` → `investigating` → `resolved` \| `reversal_confirmed`), opened_at, decided_by_id, decided_at, note | Raised when `change_pct` falls below a threshold (setting `MONITORING_ALERT_PCT`, e.g. −10%) (6.3.1) |

Rules, following the existing features:

- A job (Cloud Run job on a schedule) fetches scenes per approved project boundary, writes
  observations, and raises alerts. Actor = system in the ledger.
- The project's developer responds to an alert (like disputing an F2 flag); registry staff or an
  admin decide it, never on their own project (FR-10).
- `reversal_confirmed` cancels buffer credits equal to the lost tonnes (status `cancelled`, a new
  `registry_credit_events` entry), so tradable credits stay whole.
- An open alert does not block issuance of past vintages, but blocks issuing a new vintage — added
  to the same gate as `issuance_blocked()`.

### API and UI

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/api/monitoring/projects/{id}` | owner, assigned verifier, registry staff, admin, granted buyer | Observation timeline and alerts (WBS 6.3.2) |
| POST | `/api/monitoring/alerts/{id}/respond` | developer (own project) | Developer's explanation |
| POST | `/api/monitoring/alerts/{id}/decide` | registry staff, admin (not own project) | `resolved` or `reversal_confirmed` with a note |

The credit page's `monitoring` becomes `ok | alert | not_available` with the latest observation
date; the Home slot lists open alerts for the developer's projects.

Ledger actions: `monitoring.alert_raised` (system), `monitoring.alert_responded`,
`monitoring.alert_resolved`, `monitoring.reversal_confirmed`, `credit.buffer_cancelled`.
Buyers see these through the scoped ledger like other project entries.

## FR-11 · Inter-registry flagging hook (WBS 9.4.1)

A mechanism for future duplicate checks against other carbon registries. No external registry is
connected, so there is no counterpart to build against.

### Design

It reuses F2: an external registry's boundary is screened with the same PostGIS overlap engine
(`check_boundary`), and a match becomes a flag that blocks issuance exactly like an F2 overlap.

**Inbound — another registry reports a possible duplicate**

`POST /api/interregistry/flags`, called machine-to-machine. Authentication is a per-partner API
key (hashed in the database) or mTLS, not a user session; partners are not one of the five roles.

```json
{
  "registry": "example-registry",
  "external_project_id": "EXR-12345",
  "external_url": "https://registry.example/projects/EXR-12345",
  "geometry": { "type": "MultiPolygon", "coordinates": [] },
  "vintages": [2026, 2027],
  "methodology": "VM0047",
  "quantity_tco2e": 8400
}
```

`geometry` is GeoJSON in WGS 84 (EPSG:4326), validated by the same rules as F2 imports.
Response `201`:

```json
{
  "flag_ids": [17],
  "matches": [
    { "project_code": "CRVR-0147", "overlap_ha": 12.4, "overlap_pct": 3.1, "vintage_clash": true }
  ]
}
```

No match returns `200` with empty lists; nothing is stored. The response names only CRVR project
codes and figures that are already public in the registry.

**Outbound — CRVR shares what it has registered**

`GET /api/interregistry/boundaries?updated_since=` returns approved projects' boundaries as a
GeoJSON FeatureCollection (code, methodology, vintages, issued quantity), for partners that pull
instead of push. Same partner authentication.

### Data model

| Table | Key columns | Notes |
|---|---|---|
| `interregistry_partners` | name, api_key_hash, active, created_at | Managed by admins |
| `interregistry_flags` | partner_id FK, external_project_id, external_url, project_id FK, overlap_m2, overlap_pct, vintage_clash, status (`open` → `disputed` → `resolved`), resolution_note, resolved_by_id, resolved_at, created_at | Same lifecycle as `overlap_flags`; open and disputed flags make `issuance_blocked()` return a reason |

Ledger actions: `interregistry.flagged` (actor = system, payload has partner name and external
id), `interregistry.flag_disputed`, `interregistry.flag_resolved`. The F2 boundary page lists
these flags beside overlap flags, with the same dispute and resolve actions.

### Why this shape

- No new screening logic: the risk sits in F2, which is already tested.
- Issuance has one gate (`issuance_blocked()`), so a new source of flags cannot be forgotten by F3.
- The partner contract is plain GeoJSON plus identifiers, so any registry can implement it.
