from fastapi import APIRouter, Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.router import router as auth_router
from app.core.db import get_db
from app.features.audit.router import router as audit_router
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

api = APIRouter(prefix="/api")


@api.get("/health", tags=["system"])
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


api.include_router(auth_router)
api.include_router(registration_router)  # F1
api.include_router(boundary_router)  # F2
api.include_router(verification_router)  # F3
api.include_router(registry_router)  # F4
api.include_router(audit_router)  # F5

app.include_router(api)
