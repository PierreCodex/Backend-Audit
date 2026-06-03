from datetime import datetime, timezone

from fastapi import APIRouter

from interfaces.api.v1.schemas.respuesta import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc),
        version="0.1.0",
    )