# The /health contract. No auth. Body is exactly {"status": "ok"}.
# The boot gate, compose, and Docker HEALTHCHECK all assert on this.
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}
