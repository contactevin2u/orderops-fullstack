from fastapi import APIRouter
from ..core.config import settings

router = APIRouter(tags=["system"])

@router.get("/healthz")
def healthz():
    return {"ok": True}

@router.get("/version")
def version():
    return {"version": settings.APP_VERSION}
