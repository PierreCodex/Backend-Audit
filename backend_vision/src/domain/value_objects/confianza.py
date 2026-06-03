from dataclasses import dataclass


@dataclass(frozen=True)
class Confianza:
    """Confianza en escala 0.0–1.0 (alineada con Claude y el POS)."""

    valor: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.valor <= 1.0):
            raise ValueError(f"Confianza debe estar entre 0 y 1, recibido {self.valor}")

    def es_aceptable(self, umbral: float) -> bool:
        return self.valor >= umbral