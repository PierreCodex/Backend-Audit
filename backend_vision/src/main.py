"""Punto de entrada FastAPI con wiring completo."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from interfaces.api.dependencies import _build_pos_client
from interfaces.api.exception_handlers import registrar_handlers
from interfaces.api.middleware import registrar_middlewares
from interfaces.api.v1.routers import auditoria, capturas, health
from shared.logger import configurar_logging, get_logger

_INDEX_HTML = Path(__file__).parent / "interfaces" / "web" / "index.html"

configurar_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("backend_iniciado", version=app.version)
    yield
    pos = _build_pos_client()
    cerrar = getattr(pos, "close", None)
    if cerrar:
        await cerrar()
    log.info("backend_detenido")


app = FastAPI(
    title="Backend Visión — Auditoría Visual de Inventario",
    description="ESP32-S3-CAM → Claude Sonnet 4.6 → POS Laravel",
    version="0.1.0",
    lifespan=lifespan,
)

registrar_middlewares(app)
registrar_handlers(app)

app.include_router(health.router, prefix="/api/v1")
app.include_router(auditoria.router, prefix="/api/v1")
app.include_router(capturas.router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def interfaz_validacion() -> FileResponse:
    """Sirve la interfaz de validación (ver última captura + botón Analizar)."""
    return FileResponse(_INDEX_HTML)