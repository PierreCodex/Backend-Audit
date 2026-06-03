from dataclasses import dataclass

from domain.entities.deteccion import Deteccion
from domain.value_objects.confianza import Confianza


@dataclass(frozen=True)
class AnalisisImagen:
    """Resultado completo del análisis de Claude sobre una imagen."""

    detecciones: list[Deteccion]
    cantidad_total: int
    espacios_vacios: bool
    confianza_general: Confianza
    observaciones: str = ""

    def to_payload_pos(self) -> dict:
        """Serializa exactamente al contrato `respuesta_ia` del POS Laravel.

        Validado contra `StoreAuditoriaVisualRequest.php` de SistemaPosV2.
        """
        return {
            "cantidad_total": self.cantidad_total,
            "espacios_vacios": self.espacios_vacios,
            "confianza_general": self.confianza_general.valor,
            "productos_detectados": [
                {
                    "nombre": d.nombre,
                    "cantidad": d.cantidad,
                    "confianza": d.confianza.valor,
                }
                for d in self.detecciones
            ],
        }