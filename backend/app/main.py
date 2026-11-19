from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.auth.admin_router import router as admin_users_router
from app.auth.models import User
from app.auth.router import router as auth_router
from app.core.config import get_settings
from app.core.db import get_db
from app.core.frontend import mount_frontend
from app.features.audit.access_matrix import router as access_matrix_router
from app.features.audit.router import router as audit_router
from app.features.audit.security_log import ACCESS_DENIED, client_ip, record_security_event
from app.features.boundary.router import router as boundary_router
from app.features.registration.router import router as registration_router
from app.features.registry.router import router as registry_router
from app.features.verification.router import router as verification_router

app = FastAPI(
    title="CRVR API",
    description="Carbon Removal Verification Registry",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


@app.exception_handler(OperationalError)
def database_unavailable(request: Request, exc: OperationalError) -> JSONResponse:
    """The database is down or stopped (the hosted demo stops it overnight): say so plainly."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": get_settings().unavailable_message},
        headers={"Retry-After": "120"},
    )


@app.middleware("http")
async def log_forbidden_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    if response.status_code == status.HTTP_403_FORBIDDEN:
        db: Session | None = getattr(request.state, "db", None)
        if db is None:
            raise RuntimeError("Cannot record a forbidden request without its database session")
        user: User | None = getattr(request.state, "user", None)
        record_security_event(
            db,
            event_type=ACCESS_DENIED,
            actor_id=user.id if user else None,
            source_ip=client_ip(request),
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        )
        db.commit()
    return response


api = APIRouter(prefix="/api")


@api.get("/health", tags=["system"])
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


api.include_router(auth_router)
api.include_router(admin_users_router)
api.include_router(registration_router)  # F1
api.include_router(boundary_router)  # F2
api.include_router(verification_router)  # F3
api.include_router(registry_router)  # F4
api.include_router(audit_router)  # F5
api.include_router(access_matrix_router)  # F5

app.include_router(api)

# Production image: the built frontend on the same origin. Registered last so /api/* wins.
if static_dir := get_settings().static_dir:
    mount_frontend(app, static_dir)
