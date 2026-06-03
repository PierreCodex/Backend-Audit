from typing import Protocol

from domain.entities.analisis_imagen import AnalisisImagen


class IAnalizadorImagen(Protocol):
    """Puerto del analizador de imágenes. Implementado por ClaudeAnalizador."""

    async def analizar(self, imagen_bytes: bytes) -> AnalisisImagen: ...