"""Which sealed evidence a browser may show inline (View) instead of only downloading."""

from pathlib import Path

# The type comes from the extension, never from what the uploader claimed, so a disguised HTML
# file is never served as a page on our origin (plus `nosniff` on the response).
VIEWABLE_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def viewable_type(filename: str) -> str | None:
    """The media type to show `filename` inline with, or None when it can only be downloaded."""
    return VIEWABLE_TYPES.get(Path(filename).suffix.lower())
