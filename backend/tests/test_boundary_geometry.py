import pytest

from app.auth.models import Role
from app.features.boundary.geometry import (
    BoundaryError,
    check_geometry,
    count_other_boundaries,
    exceeds_tolerance,
    find_overlaps,
)
from app.features.boundary.models import Boundary, BoundarySource
from tests.geo import BASE, square

TOLERANCE = 0.5


@pytest.fixture
def register(db, make_project, make_user):
    """Store a boundary for a new project and return the project."""
    staff = make_user(Role.ADMIN, email="registrar@test.local")

    def _register(geojson, name="Registered project"):
        project = make_project(name=name)
        checked = check_geometry(db, geojson)
        db.add(
            Boundary(
                project_id=project.id,
                geom=checked.ewkt,
                area_m2=checked.area_m2,
                source=BoundarySource.DRAWN,
                updated_by_id=staff.id,
            )
        )
        db.flush()
        return project

    return _register


# --- validation and area --------------------------------------------------------------


def test_area_is_computed_on_the_ellipsoid(db):
    # 0.01° × 0.01° at the equator ≈ 1.113 km × 1.106 km
    checked = check_geometry(db, square(0, 0))

    assert checked.area_m2 == pytest.approx(1_230_800, rel=0.005)
    assert checked.vertices == 4
    assert checked.ewkt.startswith("SRID=4326;MULTIPOLYGON")


def test_area_shrinks_away_from_the_equator(db):
    equator = check_geometry(db, square(0, 0)).area_m2
    nan = check_geometry(db, square(*BASE)).area_m2

    # longitude degrees are shorter at 18.8° N (cos 18.8° ≈ 0.947)
    assert nan / equator == pytest.approx(0.947, abs=0.003)


def test_multipolygon_is_accepted(db):
    a, b = square(0, 0)["coordinates"], square(1, 1)["coordinates"]

    checked = check_geometry(db, {"type": "MultiPolygon", "coordinates": [a, b]})

    assert checked.vertices == 8


@pytest.mark.parametrize(
    ("geojson", "message"),
    [
        ({"type": "Point", "coordinates": [100, 18]}, "Polygon or MultiPolygon"),
        ({"type": "Polygon", "coordinates": []}, "no coordinates"),
        ({"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [0, 0]]]}, "at least 3"),
        (
            {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1]]]},
            "end where it starts",
        ),
        (
            {"type": "Polygon", "coordinates": [[[200, 0], [201, 0], [201, 1], [200, 0]]]},
            "WGS 84",
        ),
        (
            {"type": "Polygon", "coordinates": [[["a", 0], [1, 0], [1, 1], ["a", 0]]]},
            "numbers",
        ),
    ],
)
def test_malformed_input_is_rejected_with_a_clear_message(db, geojson, message):
    with pytest.raises(BoundaryError, match=message):
        check_geometry(db, geojson)


def test_self_intersecting_shape_is_rejected(db):
    bowtie = {"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]]}

    with pytest.raises(BoundaryError, match="Self-intersection"):
        check_geometry(db, bowtie)


# --- overlap detection ----------------------------------------------------------------


def test_no_overlap_when_far_apart(db, register):
    register(square(*BASE))

    checked = check_geometry(db, square(BASE[0] + 1, BASE[1]))

    assert find_overlaps(db, checked, tolerance_pct=TOLERANCE) == []


def test_boundaries_that_only_touch_do_not_overlap(db, register):
    register(square(*BASE))

    # shares the eastern edge exactly
    checked = check_geometry(db, square(BASE[0] + 0.01, BASE[1]))

    assert find_overlaps(db, checked, tolerance_pct=TOLERANCE) == []


def test_overlap_names_the_project_and_measures_the_shared_area(db, register):
    other = register(square(*BASE), name="Phrae Agroforestry")

    # shifted 0.0097° east → a 0.0003°-wide shared strip = 3% of the area
    checked = check_geometry(db, square(BASE[0] + 0.0097, BASE[1]))
    [overlap] = find_overlaps(db, checked, tolerance_pct=TOLERANCE)

    assert overlap.project_id == other.id
    assert overlap.project_code == other.code
    assert overlap.project_name == "Phrae Agroforestry"
    assert overlap.overlap_pct == pytest.approx(3.0, abs=0.01)
    assert overlap.overlap_m2 == pytest.approx(checked.area_m2 * 0.03, rel=0.001)
    assert overlap.exceeds_tolerance
    assert overlap.intersection["type"] == "Polygon"


def test_small_overlap_within_tolerance_is_reported_but_not_blocking(db, register):
    register(square(*BASE))

    # 0.2% shared strip — typical GPS error along a common edge
    checked = check_geometry(db, square(BASE[0] + 0.00998, BASE[1]))
    [overlap] = find_overlaps(db, checked, tolerance_pct=TOLERANCE)

    assert overlap.overlap_pct == pytest.approx(0.2, abs=0.01)
    assert not overlap.exceeds_tolerance


def test_overlaps_are_sorted_largest_first_and_exclude_own_project(db, register):
    small = register(square(BASE[0] + 0.0099, BASE[1]), name="small")
    large = register(square(BASE[0] - 0.005, BASE[1]), name="large")
    own = register(square(*BASE), name="own")

    checked = check_geometry(db, square(*BASE))
    overlaps = find_overlaps(db, checked, tolerance_pct=TOLERANCE, exclude_project_id=own.id)

    assert [o.project_id for o in overlaps] == [large.id, small.id]
    assert count_other_boundaries(db, exclude_project_id=own.id) == 2


@pytest.mark.parametrize(
    ("pct", "blocked"),
    [(0.49, False), (0.5, False), (0.504, False), (0.506, True), (0.51, True), (3.1, True)],
)
def test_tolerance_edge(pct, blocked):
    assert exceeds_tolerance(pct, 0.5) is blocked


def test_swallowing_a_small_project_exceeds_tolerance(db, register):
    # 0.002° square: 0.16% of the big new boundary, but 100% of its own area
    small = register(square(BASE[0] + 0.02, BASE[1] + 0.02, size=0.002))

    checked = check_geometry(db, square(*BASE, size=0.05))
    [overlap] = find_overlaps(db, checked, tolerance_pct=TOLERANCE)

    assert overlap.project_id == small.id
    assert overlap.overlap_pct == pytest.approx(0.16, abs=0.01)
    assert overlap.other_overlap_pct == pytest.approx(100, abs=0.01)
    assert overlap.exceeds_tolerance


def test_many_small_slivers_exceed_tolerance_together(db, register):
    # four neighbours, each overlapping a 0.3% strip on one side: 1.2% in total
    d = 0.00997
    for dx, dy in [(d, 0), (-d, 0), (0, d), (0, -d)]:
        register(square(BASE[0] + dx, BASE[1] + dy))

    checked = check_geometry(db, square(*BASE))
    overlaps = find_overlaps(db, checked, tolerance_pct=TOLERANCE)

    assert len(overlaps) == 4
    assert all(o.overlap_pct == pytest.approx(0.3, abs=0.01) for o in overlaps)
    assert all(o.exceeds_tolerance for o in overlaps)


def test_a_single_small_sliver_stays_within_tolerance(db, register):
    register(square(BASE[0] + 0.00997, BASE[1]))

    checked = check_geometry(db, square(*BASE))
    [overlap] = find_overlaps(db, checked, tolerance_pct=TOLERANCE)

    assert not overlap.exceeds_tolerance
