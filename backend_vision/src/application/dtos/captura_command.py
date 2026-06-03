from dataclasses import dataclass
from datetime import datetime

from domain.value_objects.nodo_id import NodoId


@dataclass(frozen=True)
class CapturaCommand:
    """Input del caso de uso ProcesarCaptura."""

    imagen_bytes: bytes
    nodo_id: NodoId
    timestamp: datetime
    tipo_evento: str = "rutina"
    request_id: str | None = None