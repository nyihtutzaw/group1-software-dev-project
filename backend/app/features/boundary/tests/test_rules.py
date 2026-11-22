"""Overlap rules per methodology with an absolute area cap (change request #43, ADR 0006)."""

import pytest

from app.auth.models import Role
from app.core.config import OverlapRuleSetting, Settings, get_settings
from app.features.boundary import service
from app.features.boundary.geometry import (
    AREA_CAP,
    COMBINED_AREA,
    SHARE_OF_THIS,
    check_geometry,
    find_overlaps,
)
from app.features.boundary.models import BoundarySource, FlagStatus, OverlapFlag
from app.features.boundary.rules import OverlapRule, exceeds_cap, rule_for
from tests.geo import BASE, square

SMALL = 0.003  # ≈ 10.5 ha near Nan — a typical agroforestry parcel
LARGE = 0.1  # ≈ 11,700 ha — a large reforestation project


@pytest.fixture
def registered(db, make_project, make_user):
    """Save a boundary for a new project with the given methodology."""
    admin = make_user(Role.ADMIN, email="registrar@test.local")

    def _registered(geojson, methodology=None):
        project = make_project(methodology=methodology)
        service.save_boundary(db, project, geojson, BoundarySource.DRAWN, admin)
        return project

    return _registered


# --- the rules ------------------------------------------------------------------------


def test_each_methodology_has_its_own_rule():
    assert rule_for("VM0047") == OverlapRule(tolerance_pct=0.5, cap_ha=10.0)
    assert rule_for("VM0042") == OverlapRule(tolerance_pct=3.0, cap_ha=1.0)
    assert rule_for("ACM0003") == OverlapRule(tolerance_pct=1.0, cap_ha=2.0)
    assert rule_for("VM0033") == OverlapRule(tolerance_pct=1.0, cap_ha=5.0)


def test_unknown_or_missing_methodology_gets_the_strict_default():
    assert rule_for(None) == OverlapRule(tolerance_pct=0.5, cap_ha=2.0)
    assert rule_for("XYZ123") == rule_for(None)


def test_two_methodologies_use_the_stricter_limit_of_each():
    pair = rule_for("VM0047").stricter(rule_for("VM0042"))
    assert pair == OverlapRule(tolerance_pct=0.5, cap_ha=1.0)


@pytest.mark.parametrize(
    ("m2", "blocked"), [(99_000, False), (100_000, False), (100_400, False), (100_600, True)]
)
def test_area_cap_edge(m2, blocked):
    # compared at the 1 decimal shown ("10.0 ha"), so exactly the cap never blocks
    assert exceeds_cap(m2, 10.0) is blocked


def test_rules_can_be_configured_from_the_environment(monkeypatch):
    monkeypatch.setenv("OVERLAP_RULES", '{"VM0042": {"tolerance_pct": 2.5, "cap_ha": 0.5}}')
    monkeypatch.setenv("OVERLAP_CAP_HA", "3")

    settings = Settings()

    assert settings.overlap_rules == {"VM0042": OverlapRuleSetting(tolerance_pct=2.5, cap_ha=0.5)}
    assert settings.overlap_cap_ha == 3.0


def test_a_changed_setting_is_used_by_the_check(db, registered, monkeypatch):
    monkeypatch.setitem(
        get_settings().overlap_rules, "VM0042", OverlapRuleSetting(tolerance_pct=1.0, cap_ha=1.0)
    )
    registered(square(*BASE, size=SMALL), methodology="VM0042")

    # 2% overlap: inside the default 3%, but above the configured 1%
    checked = check_geometry(db, square(BASE[0] + SMALL * 0.98, BASE[1], size=SMALL))
    [overlap] = find_overlaps(db, checked, rule=rule_for("VM0042"))

    assert overlap.reason == SHARE_OF_THIS


# --- the change request's two problems ------------------------------------------------


def test_small_agroforestry_parcels_are_not_flagged_for_gps_error(db, registered):
    registered(square(*BASE, size=SMALL), methodology="VM0042")
    drawn = square(BASE[0] + SMALL * 0.98, BASE[1], size=SMALL)  # 2% strip ≈ 0.2 ha

    checked = check_geometry(db, drawn)
    [overlap] = find_overlaps(db, checked, rule=rule_for("VM0042"))

    assert overlap.overlap_pct == pytest.approx(2.0, abs=0.01)
    assert overlap.reason is None
    # the old single 0.5% rule would have blocked it
    [old] = find_overlaps(db, checked, rule=OverlapRule(0.5, 1_000))
    assert old.exceeds_tolerance


def test_large_project_under_the_percentage_is_blocked_by_the_area_cap(db, registered):
    registered(square(*BASE, size=LARGE), methodology="VM0047")
    drawn = square(BASE[0] + LARGE * 0.997, BASE[1], size=LARGE)  # 0.3% strip ≈ 35 ha

    checked = check_geometry(db, drawn)
    [overlap] = find_overlaps(db, checked, rule=rule_for("VM0047"))

    assert overlap.overlap_pct == pytest.approx(0.3, abs=0.01)
    assert overlap.overlap_m2 / 10_000 == pytest.approx(35, rel=0.03)
    assert overlap.reason == AREA_CAP


def test_mixed_methodologies_use_the_stricter_rule(db, registered):
    registered(square(*BASE, size=SMALL), methodology="VM0042")
    drawn = square(BASE[0] + SMALL * 0.98, BASE[1], size=SMALL)  # 2%, fine for VM0042 alone

    checked = check_geometry(db, drawn)
    [overlap] = find_overlaps(db, checked, rule=rule_for("VM0047"))

    assert overlap.rule == OverlapRule(tolerance_pct=0.5, cap_ha=1.0)
    assert overlap.reason == SHARE_OF_THIS


def test_many_small_overlaps_together_break_the_area_cap(db, registered):
    w = 0.00003  # each strip ≈ 3.5 ha: under the 10 ha cap and far under 0.5%
    for dx, dy in [(LARGE - w, 0), (-(LARGE - w), 0), (0, LARGE - w), (0, -(LARGE - w))]:
        registered(square(BASE[0] + dx, BASE[1] + dy, size=LARGE), methodology="VM0047")

    checked = check_geometry(db, square(*BASE, size=LARGE))
    overlaps = find_overlaps(db, checked, rule=rule_for("VM0047"))

    assert len(overlaps) == 4
    assert all(o.overlap_m2 < 100_000 for o in overlaps)
    assert all(o.reason == COMBINED_AREA for o in overlaps)


# --- API and saved flags --------------------------------------------------------------


def test_check_reports_the_rule_and_why_an_overlap_blocks(
    client, login, db, registered, make_project
):
    registered(square(*BASE, size=LARGE), methodology="VM0047")
    user = login(Role.DEVELOPER)
    mine = make_project(owner=user, methodology="VM0047")

    body = client.post(
        "/api/boundaries/check",
        json={
            "geometry": square(BASE[0] + LARGE * 0.997, BASE[1], size=LARGE),
            "project_id": mine.id,
        },
    ).json()

    assert body["methodology"] == "VM0047"
    assert (body["tolerance_pct"], body["cap_ha"]) == (0.5, 10.0)
    assert body["blocked"] is True
    [overlap] = body["overlaps"]
    assert overlap["reason"] == "area_cap"
    assert (overlap["tolerance_pct"], overlap["cap_ha"]) == (0.5, 10.0)


def test_rules_endpoint_lists_every_methodology_and_the_default(client, login):
    login(Role.VERIFIER)

    body = client.get("/api/boundaries/rules").json()

    assert {r["methodology"] for r in body} == {"VM0047", "VM0042", "ACM0003", "VM0033", None}
    assert {"methodology": None, "tolerance_pct": 0.5, "cap_ha": 2.0} in body


def test_rules_endpoint_needs_sign_in(client):
    assert client.get("/api/boundaries/rules").status_code == 401


def test_saving_above_the_area_cap_flags_the_project(db, registered):
    registered(square(*BASE, size=LARGE), methodology="VM0047")

    project = registered(square(BASE[0] + LARGE * 0.997, BASE[1], size=LARGE), "VM0047")

    [flag] = db.query(OverlapFlag).filter_by(project_id=project.id).all()
    assert flag.status == FlagStatus.OPEN
    assert service.issuance_blocked(db, project.id) is not None


def test_neighbour_redraw_keeps_a_flag_still_above_the_area_cap(db, registered, make_user):
    neighbour = registered(square(*BASE, size=LARGE), methodology="VM0047")
    later = registered(square(BASE[0] + LARGE * 0.99, BASE[1], size=LARGE), "VM0047")  # 1%
    [flag] = db.query(OverlapFlag).filter_by(project_id=later.id).all()

    # the neighbour moves its edge west: the shared strip shrinks to 0.3% (≈ 35 ha) — under
    # the 0.5% tolerance, but still above the 10 ha cap, so the later project stays blocked
    admin = make_user(Role.ADMIN, email="redraw@test.local")
    moved = square(BASE[0] - LARGE * 0.007, BASE[1], size=LARGE)
    service.save_boundary(db, neighbour, moved, BoundarySource.DRAWN, admin)

    db.refresh(flag)
    assert flag.status == FlagStatus.OPEN
    assert flag.overlap_m2 / 10_000 == pytest.approx(35, rel=0.03)
    assert service.issuance_blocked(db, later.id) is not None
