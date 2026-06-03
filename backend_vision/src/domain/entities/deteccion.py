from dataclasses import dataclass

from domain.value_objects.confianza import Confianza


@dataclass(frozen=True)
class Deteccion:
    """Un producto detectado por Claude dentro de una imagen."""

    nombre: str
    cantidad: int
    confianza: Confianza

    def __post_init__(self) -> None:
        if self.cantidad < 0:
            raise ValueError(f"cantidad no puede ser negativa: {self.cantidad}")
        if not self.nombre.strip():
            raise ValueError("nombre no puede estar vacío")