# 0006 — Overlap rules per methodology, with an area cap

**Date:** 2026-11-12 · **Status:** Accepted · **Supersedes:** [0005](0005-one-overlap-tolerance-for-all-methodologies.md)

## Context

ADR 0005 kept one 0.5% overlap tolerance for every methodology and named its weak spot: small
parcels are flagged for GPS error alone. Change request #43 from the client confirms it and adds a
second problem: a percentage alone lets a large project double-count many hectares — 0.5% of a
100,000 ha project is 500 ha. The client asked for a tolerance per methodology plus an absolute
area cap, and let the team choose the defaults.

## Decision

- **Each methodology has a rule: a tolerance (% of area) and a cap (hectares).** An overlap blocks
  submission and issuance if it is above the tolerance of **either** project's area, **or** above
  the cap. All overlaps of one boundary together are also checked against both limits.
- **Two methodologies → the stricter value of each.** A reforestation project next to a farm parcel
  is checked with the lower tolerance and the lower cap of the two.
- **Defaults** (made up by the team, as the change request allows):

  | Methodology | Tolerance | Cap | Why |
  |---|---|---|---|
  | VM0047 Reforestation | 0.5% | 10 ha | Large forest blocks; the cap stops big projects double-counting under the % |
  | VM0042 Agriculture (incl. agroforestry) | 3.0% | 1 ha | Small parcels: a 10 m GPS band is ~2% of a 20 ha parcel; the cap keeps the real area small |
  | ACM0003 Soil carbon | 1.0% | 2 ha | Field parcels with surveyed edges |
  | VM0033 Tidal wetland | 1.0% | 5 ha | Shorelines move with the tide, so edges are less exact |
  | Not set / not listed | 0.5% | 2 ha | Strict default |

- **Configured in settings, not in the database.** `OVERLAP_RULES` (JSON) replaces the table above;
  `OVERLAP_TOLERANCE_PCT` and `OVERLAP_CAP_HA` set the default. A change is a reviewed config change,
  not something a user edits at run time. `GET /api/boundaries/rules` shows the rules in force.
- Comparisons use the precision shown on screen (2 decimals for %, 1 decimal for ha), so a value
  exactly at a limit never blocks.

## Consequences

- The check result names the rule applied and why an overlap blocks (`share_of_this`,
  `share_of_other`, `area_cap`, `combined_share`, `combined_area`); the Boundary page words it.
- Changing a rule does not re-screen saved boundaries. Existing flags stay as they are until a
  boundary is saved again or staff resolve them.
- The demo overlap (CRVR-0147 over CRVR-0092, 38.4 ha) is still flagged under every rule.
