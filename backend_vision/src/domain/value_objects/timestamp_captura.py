from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class TimestampCaptura:
    """Momento en que el ESP32 capturó la imagen. Siempre con timezone."""

    valor: datetime

    def __post_init__(self) -> None:
        if self.valor.tzinfo is None:
            raise ValueError("TimestampCaptura debe tener timezone (ISO 8601 con offset)")
        if self.valor > datetime.now(timezone.utc):
            raise ValueError("TimestampCaptura no puede estar en el futuro")

    def to_iso(self) -> str:
        return self.valor.isoformat()