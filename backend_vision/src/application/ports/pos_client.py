from datetime import datetime
from typing import Protocol

from application.dtos.resultado_captura import RespuestaPOS


class IPOSClient(Protocol):
    """Puerto del cliente POS. Implementado por LaravelPOSClient o MockPOSClient."""

    async def notificar_auditoria(
        self,
        nodo_id: str,
        imagen_base64: str,
        timestamp_captura: datetime,
        respuesta_ia: dict,
        tipo_evento: str = "rutina",
        request_id: str | None = None,
    ) -> RespuestaPOS: ...