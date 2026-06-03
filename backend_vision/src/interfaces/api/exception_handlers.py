"""Handlers que traducen excepciones de dominio a respuestas HTTP."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from domain.exceptions import (
    AnalizadorNoDisponible,
    CapturaInvalida,
    ConfianzaInsuficiente,
    DomainError,
    POSNoDisponible,
)
from shared.logger import get_logger

log = get_logger(__name__)


def registrar_handlers(app: FastAPI) -> None:
    @app.exception_handler(CapturaInvalida)
    async def _captura_invalida(request: Request, exc: CapturaInvalida) -> JSONResponse:
        log.warning("captura_invalida", detail=str(exc))
        return JSONResponse(
            status_code=422,
            content={"error": "captura_invalida", "detail": str(exc)},
        )

    @app.exception_handler(ConfianzaInsuficiente)
    async def _confianza_insuficiente(
        request: Request, exc: ConfianzaInsuficiente
    ) -> JSONResponse:
        log.warning("confianza_insuficiente", detail=str(exc))
        return JSONResponse(
            status_code=200,
            content={"warning": "baja_confianza", "detail": str(exc)},
        )

    @app.exception_handler(POSNoDisponible)
    async def _pos_no_disponible(request: Request, exc: POSNoDisponible) -> JSONResponse:
        log.error("pos_no_disponible", detail=str(exc))
        return JSONResponse(
            status_code=502,
            content={"error": "pos_no_disponible", "detail": str(exc)},
        )

    @app.exception_handler(AnalizadorNoDisponible)
    async def _analizador_no_disponible(
        request: Request, exc: AnalizadorNoDisponible
    ) -> JSONResponse:
        log.error("analizador_no_disponible", detail=str(exc))
        return JSONResponse(
            status_code=502,
            content={"error": "ia_no_disponible", "detail": str(exc)},
        )

    @app.exception_handler(DomainError)
    async def _domain_error(request: Request, exc: DomainError) -> JSONResponse:
        log.warning("domain_error", tipo=exc.__class__.__name__, detail=str(exc))
        return JSONResponse(
            status_code=400,
            content={"error": exc.__class__.__name__, "detail": str(exc)},
        )

    @app.exception_handler(ValueError)
    async def _value_error(request: Request, exc: ValueError) -> JSONResponse:
        log.warning("value_error", detail=str(exc))
        return JSONResponse(
            status_code=422,
            content={"error": "valor_invalido", "detail": str(exc)},
        )