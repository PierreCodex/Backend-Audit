"""Endpoints de la interfaz de validación local.

Listan las capturas que el ESP32 dejó en `storage/debug/`, sirven la imagen y dejan
correr Claude bajo demanda (botón "Analizar"). NO tocan el POS ni dependen de
`ANALISIS_AUTOMATICO`: están pensados para validar el conteo de Claude en aislamiento
antes de conectar el POS Laravel. Sin auth (herramienta de desarrollo local).
"""
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from infrastructure.ia.claude_analizador import ClaudeAnalizador
from interfaces.api.dependencies import get_analizador
from interfaces.api.security import verificar_token_esp32
from interfaces.api.v1.schemas.conteo import (
    CapturaItem,
    ConteoResponse,
    ProductoDetectado,
)
from shared.config import Settings, get_settings
from shared.logger import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/capturas", tags=["capturas"])

# Extensiones que guarda el backend (ver capturas_storage._extension_por_magic_bytes).
_EXTENSIONES = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# Bandera en memoria para la "captura manual bajo demanda". La UI la pone en True
# (botón "Capturar ahora") y el ESP32 la consume al preguntar GET /pendiente (sentido
# saliente ESP32→backend, el confiable). Estado de proceso único (uvicorn 1 worker).
_captura_solicitada = False


def _carpeta_debug(settings: Settings) -> Path:
    return Path(settings.storage_path) / "debug"


def _resolver_captura(nombre: str, settings: Settings) -> Path:
    """Resuelve un nombre a una ruta dentro de debug/, bloqueando path traversal."""
    carpeta = _carpeta_debug(settings).resolve()
    ruta = (carpeta / nombre).resolve()
    # La ruta resuelta debe seguir colgando de la carpeta debug (evita ../).
    if carpeta not in ruta.parents or not ruta.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Captura no encontrada: {nombre}",
        )
    return ruta


def _a_item(ruta: Path) -> CapturaItem:
    stat = ruta.stat()
    # Railway corre en UTC; sin tz explícita el navegador interpreta como local → bug.
    return CapturaItem(
        nombre=ruta.name,
        bytes=stat.st_size,
        modificado=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    )


def _listar(settings: Settings) -> list[Path]:
    """Capturas de debug/, más recientes primero."""
    carpeta = _carpeta_debug(settings)
    if not carpeta.is_dir():
        return []
    archivos = [
        p for p in carpeta.iterdir() if p.is_file() and p.suffix.lower() in _EXTENSIONES
    ]
    return sorted(archivos, key=lambda p: p.stat().st_mtime, reverse=True)


@router.get("", response_model=list[CapturaItem], summary="Lista las capturas guardadas")
def listar_capturas(settings: Settings = Depends(get_settings)) -> list[CapturaItem]:
    return [_a_item(p) for p in _listar(settings)]


@router.get(
    "/ultima",
    response_model=CapturaItem,
    summary="La captura más reciente (para refresco automático)",
)
def ultima_captura(settings: Settings = Depends(get_settings)) -> CapturaItem:
    capturas = _listar(settings)
    if not capturas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todavía no hay capturas en storage/debug/",
        )
    return _a_item(capturas[0])


@router.post(
    "/solicitar",
    summary="Pide una captura manual (la UI marca; el ESP32 la recoge al hacer polling)",
)
def solicitar_captura() -> dict:
    global _captura_solicitada
    _captura_solicitada = True
    log.info("captura_manual_solicitada")
    return {"solicitado": True}


@router.get(
    "/pendiente",
    dependencies=[Depends(verificar_token_esp32)],
    summary="El ESP32 pregunta si hay una captura manual pendiente (consume la bandera)",
)
def captura_pendiente() -> dict:
    global _captura_solicitada
    pendiente = _captura_solicitada
    _captura_solicitada = False  # consume-on-read: dispara una sola captura por solicitud
    if pendiente:
        log.info("captura_pendiente_entregada_al_esp32")
    return {"pendiente": pendiente}


@router.get("/{nombre}/imagen", summary="Sirve los bytes de una captura")
def imagen_captura(
    nombre: str, settings: Settings = Depends(get_settings)
) -> FileResponse:
    ruta = _resolver_captura(nombre, settings)
    return FileResponse(ruta)


@router.post(
    "/{nombre}/analizar",
    response_model=ConteoResponse,
    summary="Corre Claude sobre la captura y devuelve el desglose (sin POS)",
)
async def analizar_captura(
    nombre: str,
    analizador: ClaudeAnalizador = Depends(get_analizador),
    settings: Settings = Depends(get_settings),
) -> ConteoResponse:
    ruta = _resolver_captura(nombre, settings)
    imagen_bytes = ruta.read_bytes()

    log.info("analisis_manual_iniciado", nombre=nombre, bytes=len(imagen_bytes))
    analisis = await analizador.analizar(imagen_bytes)
    log.info(
        "analisis_manual_ok",
        nombre=nombre,
        cantidad_total=analisis.cantidad_total,
        confianza=analisis.confianza_general.valor,
    )

    return ConteoResponse(
        nombre=nombre,
        productos=[
            ProductoDetectado(
                nombre=d.nombre, cantidad=d.cantidad, confianza=d.confianza.valor
            )
            for d in analisis.detecciones
        ],
        cantidad_total=analisis.cantidad_total,
        confianza_general=analisis.confianza_general.valor,
        espacios_vacios=analisis.espacios_vacios,
        observaciones=analisis.observaciones,
    )
