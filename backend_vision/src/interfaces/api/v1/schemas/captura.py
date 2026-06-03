from pydantic import BaseModel, Field


class CapturaResponse(BaseModel):
    """Response que el backend Python devuelve al ESP32 tras procesar una captura."""

    auditoria_id_pos: int = Field(..., description="ID asignado por el POS Laravel")
    accion_tomada: str = Field(
        ...,
        description="pendiente | validada_venta | merma_sospechosa | reposicion_confirmada",
    )
    cantidad_total: int = Field(..., ge=0)
    confianza_general: float = Field(..., ge=0.0, le=1.0)
    espacios_vacios: bool
    idempotent_replay: bool = Field(
        default=False,
        description="True si el POS detectó que es un reintento del mismo request_id",
    )