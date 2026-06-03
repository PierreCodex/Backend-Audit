from dataclasses import dataclass


@dataclass(frozen=True)
class NodoId:
    """Identificador del ESP32 emisor. Normalmente la MAC (ej. 14:c1:9f:c1:b7:60)."""

    valor: str

    def __post_init__(self) -> None:
        if not self.valor or len(self.valor) < 12:
            raise ValueError(f"NodoId inválido: {self.valor!r}")