"""Overlap rules per methodology (change request #43, ADR 0006).

Each methodology allows overlap up to a share of the area (`tolerance_pct`, absorbs GPS and
drawing error, which matters most for small parcels) and up to an absolute area (`cap_ha`, so a
large project cannot double-count many hectares while staying under the percentage). When two
projects with different methodologies overlap, the stricter value of each applies.

Values come from settings (`OVERLAP_RULES`); a project with no listed methodology gets the strict
default (`OVERLAP_TOLERANCE_PCT`, `OVERLAP_CAP_HA`).
"""

from dataclasses import dataclass

from app.core.config import get_settings

M2_PER_HA = 10_000


@dataclass(frozen=True)
class OverlapRule:
    tolerance_pct: float
    cap_ha: float

    def stricter(self, other: "OverlapRule") -> "OverlapRule":
        """The rule for an overlap between two projects: the lower limit of each."""
        return OverlapRule(
            min(self.tolerance_pct, other.tolerance_pct), min(self.cap_ha, other.cap_ha)
        )


def rule_for(methodology: str | None) -> OverlapRule:
    settings = get_settings()
    rule = settings.overlap_rules.get(methodology or "")
    if rule is None:
        return OverlapRule(settings.overlap_tolerance_pct, settings.overlap_cap_ha)
    return OverlapRule(rule.tolerance_pct, rule.cap_ha)


def all_rules() -> dict[str, OverlapRule]:
    """Every configured methodology rule (for display)."""
    return {code: rule_for(code) for code in get_settings().overlap_rules}


def exceeds_tolerance(overlap_pct: float, tolerance_pct: float) -> bool:
    """True if the overlap is above tolerance. Compared at the 2 decimals shown to users,
    so "0.50%" against a 0.5% tolerance is never blocked."""
    return round(overlap_pct, 2) > tolerance_pct


def exceeds_cap(overlap_m2: float, cap_ha: float) -> bool:
    """True if the overlap is above the area cap. Compared at the 1 decimal shown to users
    ("10.0 ha"), so exactly the cap is never blocked."""
    return round(overlap_m2 / M2_PER_HA, 1) > cap_ha
