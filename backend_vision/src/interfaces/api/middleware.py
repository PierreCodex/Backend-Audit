"""Middleware: correlation ID + logging estructurado por request."""
import time
import uuid

import structlog
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from shared.logger import get_logger

log = get_logger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Lee `X-Request-Id` o genera uno y lo inyecta en el contexto de structlog."""

    HEADER = "X-Request-Id"

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get(self.HEADER) or str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            path=request.url.path,
            method=request.method,
        )

        inicio = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log.exception("request_error_no_capturado")
            raise

        duracion_ms = round((time.perf_counter() - inicio) * 1000, 2)
        log.info("request_procesado", status=response.status_code, duracion_ms=duracion_ms)

        response.headers[self.HEADER] = correlation_id
        return response


def registrar_middlewares(app: FastAPI) -> None:
    """Agrega CORS + Correlation ID al app."""
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # demo: abrir; producción: restringir
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CorrelationIdMiddleware)