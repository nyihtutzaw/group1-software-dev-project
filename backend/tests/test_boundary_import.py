import io
import json
import zipfile

import pytest
import shapefile

from app.features.boundary.geometry import BoundaryError, check_geometry
from app.features.boundary.importers import parse_boundary_file
from tests.geo import BASE, square

WGS84_PRJ = (
    'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],'
    'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
)
UTM_PRJ = 'PROJCS["WGS_1984_UTM_Zone_47N",GEOGCS["GCS_WGS_1984"]]'

KML = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark><name>Parcel</name>
<Polygon>
  <outerBoundaryIs><LinearRing><coordinates>
    100.77,18.78,0 100.79,18.78,0 100.79,18.80,0 100.77,18.80,0 100.77,18.78,0
  </coordinates></LinearRing></outerBoundaryIs>
  <innerBoundaryIs><LinearRing><coordinates>
    100.775,18.785 100.776,18.785 100.776,18.786 100.775,18.785
  </coordinates></LinearRing></innerBoundaryIs>
</Polygon></Placemark></Document></kml>"""


def zipped(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def shapefile_zip(polygons: list, prj: str | None = WGS84_PRJ) -> bytes:
    shp, shx, dbf = io.BytesIO(), io.BytesIO(), io.BytesIO()
    with shapefile.Writer(shp=shp, shx=shx, dbf=dbf, shapeType=shapefile.POLYGON) as writer:
        writer.field("name", "C")
        for rings in polygons:
            writer.poly(rings)
            writer.record("parcel")
    files = {
        "parcel.shp": shp.getvalue(),
        "parcel.shx": shx.getvalue(),
        "parcel.dbf": dbf.getvalue(),
    }
    if prj:
        files["parcel.prj"] = prj.encode()
    return zipped(files)


# --- GeoJSON --------------------------------------------------------------------------


def test_geojson_feature_collection_merges_polygons():
    doc = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": square(*BASE), "properties": {}},
            {"type": "Feature", "geometry": square(BASE[0] + 1, BASE[1]), "properties": {}},
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [0, 0]}},
        ],
    }

    geometry = parse_boundary_file("parcels.geojson", json.dumps(doc).encode())

    assert geometry["type"] == "MultiPolygon"
    assert len(geometry["coordinates"]) == 2


def test_geojson_single_feature_and_bare_geometry():
    feature = {"type": "Feature", "geometry": square(*BASE)}

    assert parse_boundary_file("a.json", json.dumps(feature).encode()) == square(*BASE)
    assert parse_boundary_file("b.geojson", json.dumps(square(*BASE)).encode()) == square(*BASE)


def test_geojson_in_projected_crs_is_rejected():
    doc = {**square(*BASE), "crs": {"type": "name", "properties": {"name": "EPSG:32647"}}}

    with pytest.raises(BoundaryError, match="WGS 84"):
        parse_boundary_file("utm.geojson", json.dumps(doc).encode())


def test_geojson_without_polygons_is_rejected():
    with pytest.raises(BoundaryError, match="No polygon"):
        parse_boundary_file("p.geojson", b'{"type": "Point", "coordinates": [1, 2]}')


def test_invalid_json_is_rejected():
    with pytest.raises(BoundaryError, match="not valid JSON"):
        parse_boundary_file("broken.geojson", b"{nope")


# --- KML / KMZ ------------------------------------------------------------------------


def test_kml_polygon_with_hole(db):
    geometry = parse_boundary_file("parcel.kml", KML.encode())

    assert geometry["type"] == "Polygon"
    assert len(geometry["coordinates"]) == 2  # outer ring + hole
    assert geometry["coordinates"][0][0] == [100.77, 18.78]
    assert check_geometry(db, geometry).area_m2 > 0


def test_kmz_is_unzipped():
    geometry = parse_boundary_file("parcel.kmz", zipped({"doc.kml": KML.encode()}))

    assert geometry["type"] == "Polygon"


def test_kml_entities_are_not_expanded():
    evil = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><kml>&a;</kml>'

    with pytest.raises(BoundaryError, match="could not be read"):
        parse_boundary_file("evil.kml", evil)


# --- shapefile ------------------------------------------------------------------------


def test_zipped_shapefile(db):
    data = shapefile_zip([square(*BASE)["coordinates"]])

    geometry = parse_boundary_file("parcel.zip", data)

    assert geometry["type"] == "Polygon"
    assert check_geometry(db, geometry).area_m2 == pytest.approx(
        check_geometry(db, square(*BASE)).area_m2, rel=1e-6
    )


def test_shapefile_with_several_parcels_becomes_multipolygon():
    data = shapefile_zip(
        [square(*BASE)["coordinates"], square(BASE[0] + 1, BASE[1])["coordinates"]]
    )

    assert parse_boundary_file("parcels.zip", data)["type"] == "MultiPolygon"


def test_projected_shapefile_is_rejected():
    with pytest.raises(BoundaryError, match="projected coordinate system"):
        parse_boundary_file("utm.zip", shapefile_zip([square(*BASE)["coordinates"]], prj=UTM_PRJ))


def test_zip_without_shapefile_is_rejected():
    with pytest.raises(BoundaryError, match=".shp and .shx"):
        parse_boundary_file("notes.zip", zipped({"readme.txt": b"hello"}))


def test_unsupported_extension_is_rejected():
    with pytest.raises(BoundaryError, match="Unsupported file type '.pdf'"):
        parse_boundary_file("survey.pdf", b"%PDF")
