# 0005 — One overlap tolerance for all methodologies

**Date:** 2026-11-03 · **Status:** Superseded by [0006](0006-overlap-rules-per-methodology.md) (change request #43)

## Context

F2 flags a boundary overlap above 0.5% (`OVERLAP_TOLERANCE_PCT`) and blocks issuance until registry
staff resolve it. The question was whether each methodology (VM0047 reforestation, VM0042
agriculture, ACM0003 soil carbon, VM0033 blue carbon) should have its own tolerance (issue #24).

The tolerance exists for one reason: to absorb GPS and drawing error along an edge two projects
share. Anything above it is treated as possible double counting.

## Decision

- **One registry-wide tolerance (0.5%) for every methodology.** No per-methodology setting.
- Edge error depends on **how the boundary was surveyed** (handheld GPS, survey-grade GPS,
  digitised from a map, tree cover), not on the carbon methodology. Two projects of different
  methodologies can share an edge, so per-methodology values would also need a rule for which one
  applies.
- Double counting matters equally for every methodology, so none of them gets a looser limit.

## Consequences

- No code change: `OVERLAP_TOLERANCE_PCT` stays the single setting, and the check stays as it is.
- **Known limit: small projects.** The tolerance is a share of the area, but edge error grows with
  the length of the edge. A 10 m error band along one side of a square is about 0.3% of a
  1,000 ha project but about 2.2% of a 20 ha one. Small parcels are therefore more likely to be
  flagged for GPS error alone. Staff can resolve these flags with a note today.
- If small projects get many such flags, the next step is an **absolute allowance** (e.g. an
  overlap under a set number of square metres never blocks), not per-methodology percentages.
