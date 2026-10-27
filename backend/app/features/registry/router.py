"""F4 Public registry & buyer transparency — API routes, mounted under /api/registry."""

from fastapi import APIRouter

router = APIRouter(prefix="/registry", tags=["F4 registry"])


@router.get("/credits")
def list_credits() -> list[dict]:
    """Issued credits. Public: no sign-in required. Placeholder until F4 is built."""
    return []
