"""Guardado opcional de capturas a disco para inspección visual durante el desarrollo.

Activado por la flag `DEBUG_GUARDAR_CAPTURAS=true` en `.env`. Las imágenes quedan en
`<STORAGE_PATH>/debug/` con nombre informativo (timestamp + nodo + correlation + bytes).
"""
from pathlib import Path

from shared.logger import get_logger

log = get_logger(__name__)


def _extension_por_magic_bytes(imagen_bytes: bytes) -> str:
    if imagen_bytes.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if imagen_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if imagen_bytes.startswith(b"GIF87a") or imagen_bytes.startswith(b"GIF89a"):
        return "gif"
    if imagen_bytes[:4] == b"RIFF" and imagen_bytes[8:12] == b"WEBP":
        return "webp"
    return "bin"


def guardar_captura_debug(
    *,
    storage_path: str,
    imagen_bytes: bytes,
    nodo_id: str,
    correlation_id: str,
    timestamp_iso: str,
) -> Path:
    """Persiste una imagen recibida en disco para inspección. Devuelve la ruta."""
    carpeta = Path(storage_path) / "debug"
    carpeta.mkdir(parents=True, exist_ok=True)

    # Sanitizar nodo_id (puede tener `:` que rompe Windows)
    nodo_safe = nodo_id.replace(":", "").replace("/", "_")
    ts_safe = timestamp_iso.replace(":", "-").replace(".", "-")

    nombre = f"{ts_safe}__{nodo_safe}__{correlation_id[:8]}__{len(imagen_bytes)}b.{_extension_por_magic_bytes(imagen_bytes)}"
    ruta = carpeta / nombre

    ruta.write_bytes(imagen_bytes)
    log.info("debug_imagen_guardada", ruta=str(ruta), bytes=len(imagen_bytes))
    return ruta