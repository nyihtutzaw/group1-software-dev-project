"""Small GeoJSON builders for boundary tests."""


def square(lon: float, lat: float, size: float = 0.01) -> dict:
    """An axis-aligned square polygon with its south-west corner at (lon, lat), in degrees."""
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [lon, lat],
                [lon + size, lat],
                [lon + size, lat + size],
                [lon, lat + size],
                [lon, lat],
            ]
        ],
    }


# Base parcel used across tests: a 0.01° square near Nan, Thailand (~1.17 km²)
BASE = (100.77, 18.78)
