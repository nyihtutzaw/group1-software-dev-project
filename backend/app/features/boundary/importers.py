"""Read a project boundary from an uploaded file (WBS 5.1.3).

Supported: GeoJSON (.geojson/.json), KML (.kml), KMZ (.kmz) and zipped ESRI shapefiles (.zip).
Every reader returns a GeoJSON Polygon or MultiPolygon in WGS 84; check_geometry() then validates
it. Files are untrusted: XML is parsed with defusedxml and zip archives are size-checked.
"""

import io
import json
import zipfile
from pathlib import PurePosixPath
from typing import Any

import shapefile
from defusedxml import ElementTree

from app.features.boundary.geometry import BoundaryError

SUPPORTED = "GeoJSON (.geojson), KML (.kml / .kmz) or a zipped shapefile (.zip)"
MAX_UNZIPPED_BYTES = 50 * 1024 * 1024
WGS84_CRS = {"EPSG:4326", "urn:ogc:def:crs:OGC:1.3:CRS84", "urn:ogc:def:crs:EPSG::4326"}

Rings = list[list[list[float]]]


def parse_boundary_file(filename: str, data: bytes) -> dict[str, Any]:
    """Return the polygons in the file as one GeoJSON geometry. Raises BoundaryError."""
    suffix = PurePosixPath(filename.lower()).suffix
    if suffix in (".geojson", ".json"):
        polygons = _from_geojson(data)
    elif suffix == ".kml":
        polygons = _from_kml(data)
    elif suffix == ".kmz":
        polygons = _from_kml(_read_from_zip(data, ".kml"))
    elif suffix == ".zip":
        polygons = _from_shapefile_zip(data)
    else:
        raise BoundaryError(f"Unsupported file type '{suffix or filename}'. Use {SUPPORTED}.")

    if not polygons:
        raise BoundaryError("No polygon found in the file.")
    if len(polygons) == 1:
        return {"type": "Polygon", "coordinates": polygons[0]}
    return {"type": "MultiPolygon", "coordinates": polygons}


# --- GeoJSON --------------------------------------------------------------------------


def _from_geojson(data: bytes) -> list[Rings]:
    try:
        doc = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BoundaryError("The GeoJSON file is not valid JSON.") from exc
    if not isinstance(doc, dict):
        raise BoundaryError("The GeoJSON file must contain an object.")

    crs = _get(_get(doc, "crs"), "properties")
    crs_name = _get(crs, "name")
    if crs_name and (not isinstance(crs_name, str) or crs_name not in WGS84_CRS):
        raise BoundaryError(f"The GeoJSON uses {crs_name}; re-export it in WGS 84 (EPSG:4326).")

    if doc.get("type") == "FeatureCollection":
        features = doc.get("features")
        if not isinstance(features, list):
            raise BoundaryError("The GeoJSON FeatureCollection has no features list.")
        geometries = [_get(f, "geometry") for f in features]
    elif doc.get("type") == "Feature":
        geometries = [doc.get("geometry")]
    else:
        geometries = [doc]

    polygons: list[Rings] = []
    for geometry in geometries:
        if not isinstance(geometry, dict):
            continue
        if geometry.get("type") == "Polygon":
            polygons.append(geometry.get("coordinates"))
        elif geometry.get("type") == "MultiPolygon":
            polygons.extend(geometry.get("coordinates") or [])
    return polygons


def _get(value: Any, key: str) -> Any:
    """`value[key]` if `value` is a JSON object, else None — uploaded JSON can be any shape."""
    return value.get(key) if isinstance(value, dict) else None


# --- KML / KMZ ------------------------------------------------------------------------


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]  # drop the XML namespace


def _kml_ring(element: Any) -> list[list[float]]:
    for node in element.iter():
        if _local(node.tag) == "coordinates" and node.text:
            ring = []
            for token in node.text.split():
                parts = token.split(",")
                try:
                    ring.append([float(parts[0]), float(parts[1])])
                except (IndexError, ValueError) as exc:
                    raise BoundaryError(f"Unreadable KML coordinate '{token}'.") from exc
            return ring
    return []


def _from_kml(data: bytes) -> list[Rings]:
    try:
        root = ElementTree.fromstring(data)
    except Exception as exc:  # malformed or malicious XML
        raise BoundaryError("The KML file could not be read.") from exc

    polygons: list[Rings] = []
    for polygon in root.iter():
        if _local(polygon.tag) != "Polygon":
            continue
        outer: list[list[float]] = []
        inner: Rings = []
        for child in polygon:
            if _local(child.tag) == "outerBoundaryIs":
                outer = _kml_ring(child)
            elif _local(child.tag) == "innerBoundaryIs":
                inner.append(_kml_ring(child))
        if outer:
            polygons.append([outer, *inner])
    return polygons


# --- zip archives / shapefiles --------------------------------------------------------


def _open_zip(data: bytes) -> zipfile.ZipFile:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise BoundaryError("The file is not a valid zip archive.") from exc
    if sum(info.file_size for info in archive.infolist()) > MAX_UNZIPPED_BYTES:
        raise BoundaryError("The archive is too large once unzipped.")
    return archive


def _read_from_zip(data: bytes, suffix: str) -> bytes:
    archive = _open_zip(data)
    for name in archive.namelist():
        if name.lower().endswith(suffix) and not name.startswith("__MACOSX/"):
            return archive.read(name)
    raise BoundaryError(f"No {suffix} file found inside the archive.")


def _prj_is_wgs84(prj: str) -> bool:
    text = prj.upper()
    return "PROJCS" not in text and "GEOGCS" in text and "WGS" in text and "84" in text


def _from_shapefile_zip(data: bytes) -> list[Rings]:
    archive = _open_zip(data)
    names = {PurePosixPath(n).suffix.lower(): n for n in archive.namelist() if "__MACOSX" not in n}
    if ".shp" not in names or ".shx" not in names:
        raise BoundaryError("The zip must contain a shapefile (.shp and .shx, ideally .prj).")
    if ".prj" in names and not _prj_is_wgs84(archive.read(names[".prj"]).decode(errors="ignore")):
        raise BoundaryError(
            "The shapefile is in a projected coordinate system; re-export it in WGS 84 (EPSG:4326)."
        )

    try:
        reader = shapefile.Reader(
            shp=io.BytesIO(archive.read(names[".shp"])),
            shx=io.BytesIO(archive.read(names[".shx"])),
            dbf=io.BytesIO(archive.read(names[".dbf"])) if ".dbf" in names else None,
        )
        shapes = reader.shapes()
    except Exception as exc:
        raise BoundaryError("The shapefile could not be read.") from exc

    polygons: list[Rings] = []
    for shape in shapes:
        geometry = shape.__geo_interface__
        if geometry["type"] == "Polygon":
            polygons.append(_as_lists(geometry["coordinates"]))
        elif geometry["type"] == "MultiPolygon":
            polygons.extend(_as_lists(p) for p in geometry["coordinates"])
    return polygons


def _as_lists(polygon: Any) -> Rings:
    """pyshp returns tuples (and may include Z/M values); keep plain [lon, lat] lists."""
    return [[[float(p[0]), float(p[1])] for p in ring] for ring in polygon]
