"""Configuración de structlog para logs estructurados JSON."""
import logging
import sys

import structlog


def configurar_logging(nivel: str = "INFO") -> None:
    """Configura structlog para emitir JSON a stdout (Railway/Docker lo capturan)."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, nivel.upper(), logging.INFO),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, nivel.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(nombre: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(nombre)