"""Cliente HTTP async hacia el POS Laravel. Implementa IPOSClient."""
from datetime import datetime

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from application.dtos.resultado_captura import RespuestaPOS
from domain.exceptions import POSNoDisponible
from shared.logger import get_logger

log = get_logger(__name__)


class LaravelPOSClient:
    """Llama al endpoint POST /api/vision/auditoria/registrar del POS Laravel.

    Contrato validado contra StoreAuditoriaVisualRequest.php de SistemaPosV2.
    """

    def __init__(self, base_url: str, token: str, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    async def notificar_auditoria(
        self,
        nodo_id: str,
        imagen_base64: str,
        timestamp_captura: datetime,
        respuesta_ia: dict,
        tipo_evento: str = "rutina",
        request_id: str | None = None,
    ) -> RespuestaPOS:
        payload: dict = {
            "nodo_id": nodo_id,
            "imagen_base64": imagen_base64,
            "timestamp_captura": timestamp_captura.isoformat(),
            "tipo_evento": tipo_evento,
            "respuesta_ia": respuesta_ia,
        }
        if request_id:
            payload["request_id"] = request_id

        try:
            data = await self._post_con_reintentos(payload)
        except httpx.HTTPStatusError as e:
            log.error(
                "pos_rechazo",
                status=e.response.status_code,
                body=e.response.text[:500],
                nodo_id=nodo_id,
            )
            raise POSNoDisponible(
                f"POS respondió {e.response.status_code}: {e.response.text[:200]}"
            ) from e
        except httpx.HTTPError as e:
            log.error("pos_http_error", error=str(e), nodo_id=nodo_id)
            raise POSNoDisponible(f"Error de red al POS: {e}") from e

        return RespuestaPOS(
            auditoria_id=int(data["auditoria_id"]),
            accion_tomada=str(data["accion_tomada"]),
            idempotent_replay=bool(data.get("idempotent_replay", False)),
        )

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    async def _post_con_reintentos(self, payload: dict) -> dict:
        res = await self._client.post("/api/vision/auditoria/registrar", json=payload)
        res.raise_for_status()
        return res.json()

    async def close(self) -> None:
        await self._client.aclose()