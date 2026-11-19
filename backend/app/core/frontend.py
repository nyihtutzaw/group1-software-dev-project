"""Serve the built frontend from the API app (production image only).

In production one Cloud Run service runs both: /api/* is the API and every other path is the React
app, so the browser stays on one origin and the httpOnly session cookie needs no CORS setup. In
development STATIC_DIR is empty and Vite serves the frontend instead.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Vite fingerprints everything under /assets, so those files can be cached for good.
IMMUTABLE = {"Cache-Control": "public, max-age=31536000, immutable"}
# index.html names the current asset files; always fetch it fresh so a deploy shows up at once.
NO_CACHE = {"Cache-Control": "no-cache"}


def mount_frontend(app: FastAPI, directory: str) -> None:
    root = Path(directory).resolve()
    index = root / "index.html"
    if not index.is_file():
        raise RuntimeError(f"STATIC_DIR={directory} has no index.html; build the frontend first")

    if (root / "assets").is_dir():
        app.mount("/assets", _ImmutableStaticFiles(directory=root / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        # Unknown API paths stay JSON 404s instead of returning the app's HTML.
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Not Found")
        file = (root / path).resolve()
        if path and file.is_file() and file.is_relative_to(root):
            return FileResponse(file)  # favicon, robots.txt, other files from public/
        # Client-side routes (/projects/12, /ledger, …) all load the React app.
        return FileResponse(index, headers=NO_CACHE)


class _ImmutableStaticFiles(StaticFiles):
    def file_response(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        response = super().file_response(*args, **kwargs)
        response.headers.update(IMMUTABLE)
        return response
