"""Schemas para la interfaz de validación (lista de capturas + conteo de Claude).

Estos endpoints son una herramienta de validación local: muestran las imágenes que
guarda el ESP32 en `storage/debug/` y dejan correr Claude bajo demanda sin tocar el POS.
"""
from pydantic import BaseModel, Field


class CapturaItem(BaseModel):
    """Una captura guardada en disco."""

    nombre: str = Field(..., description="Nombre de archivo en storage/debug/")
    bytes: int = Field(..., ge=0, description="Tamaño del archivo")
    modificado: str = Field(..., description="Fecha de modificación (ISO 8601)")


class ProductoDetectado(BaseModel):
    nombre: str
    cantidad: int = Field(..., ge=0)
    confianza: float = Field(..., ge=0.0, le=1.0)


class ConteoResponse(BaseModel):
    """Desglose completo de Claude sobre una imagen, sin pasar por el POS."""

    nombre: str = Field(..., description="Imagen analizada")
    productos: list[ProductoDetectado]
    cantidad_total: int = Field(..., ge=0)
    confianza_general: float = Field(..., ge=0.0, le=1.0)
    espacios_vacios: bool
    observaciones: str = ""
