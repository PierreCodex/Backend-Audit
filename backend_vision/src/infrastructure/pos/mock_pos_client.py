"""POS falso para desarrollo offline y tests."""
from datetime import datetime

from application.dtos.resultado_captura import RespuestaPOS


class MockPOSClient:
    """Implementa IPOSClient por duck typing. Guarda las llamadas para inspección en tests."""

    def __init__(self) -> None:
        self.llamadas: list[dict] = []
        self._next_id = 1
        self._vistos_request_ids: set[str] = set()

    async def notificar_auditoria(
        self,
        nodo_id: str,
        imagen_base64: str,
        timestamp_captura: datetime,
        respuesta_ia: dict,
        tipo_evento: str = "rutina",
        request_id: str | None = None,
    ) -> RespuestaPOS:
        # Simula idempotencia del POS real cuando llegue el ajuste de POS_AJUSTES_PENDIENTES.md
        if request_id and request_id in self._vistos_request_ids:
            previa = next(
                (c for c in self.llamadas if c.get("request_id") == request_id), None
            )
            if previa:
                return RespuestaPOS(
                    auditoria_id=previa["auditoria_id"],
                    accion_tomada=previa["accion_tomada"],
                    idempotent_replay=True,
                )

        auditoria_id = self._next_id
        self._next_id += 1

        # Decidir acción según el conteo (heurística simple para mocks)
        cantidad_total = int(respuesta_ia.get("cantidad_total", 0))
        accion = "pendiente" if cantidad_total == 0 else "validada_venta"

        registro = {
            "auditoria_id": auditoria_id,
            "accion_tomada": accion,
            "nodo_id": nodo_id,
            "timestamp_captura": timestamp_captura,
            "tipo_evento": tipo_evento,
            "respuesta_ia": respuesta_ia,
            "request_id": request_id,
            "imagen_bytes_b64_len": len(imagen_base64),
        }
        self.llamadas.append(registro)
        if request_id:
            self._vistos_request_ids.add(request_id)

        return RespuestaPOS(auditoria_id=auditoria_id, accion_tomada=accion)