"""Adaptador de Claude Sonnet 4.6 (multimodal). Implementa IAnalizadorImagen."""
import base64
import json

from anthropic import APIError, AsyncAnthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from domain.entities.analisis_imagen import AnalisisImagen
from domain.entities.deteccion import Deteccion
from domain.exceptions import AnalizadorNoDisponible
from domain.value_objects.confianza import Confianza
from infrastructure.ia.prompts import PROMPT_AUDITORIA
from shared.logger import get_logger

log = get_logger(__name__)


class ClaudeAnalizador:
    """Llama a la Messages API de Anthropic con la imagen en base64."""

    def __init__(self, client: AsyncAnthropic, modelo: str, max_tokens: int = 1024) -> None:
        self._client = client
        self._modelo = modelo
        self._max_tokens = max_tokens

    async def analizar(self, imagen_bytes: bytes) -> AnalisisImagen:
        b64 = base64.standard_b64encode(imagen_bytes).decode("ascii")
        media_type = self._detectar_media_type(imagen_bytes)

        try:
            raw = await self._llamar_claude(b64, media_type)
        except APIError as e:
            log.error("claude_api_error", status=getattr(e, "status_code", None), error=str(e))
            raise AnalizadorNoDisponible(f"Claude API falló: {e}") from e
        except Exception as e:
            log.error("claude_error_inesperado", error=str(e))
            raise AnalizadorNoDisponible(f"Error inesperado llamando a Claude: {e}") from e

        try:
            data = self._extraer_json(raw)
        except (ValueError, json.JSONDecodeError) as e:
            log.error("claude_respuesta_no_json", raw=raw[:500])
            raise AnalizadorNoDisponible(f"Claude devolvió un texto no parseable: {e}") from e

        return self._mapear(data)

    @retry(
        retry=retry_if_exception_type(APIError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _llamar_claude(self, imagen_b64: str, media_type: str) -> str:
        response = await self._client.messages.create(
            model=self._modelo,
            max_tokens=self._max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": imagen_b64,
                            },
                        },
                        {"type": "text", "text": PROMPT_AUDITORIA},
                    ],
                }
            ],
        )
        if not response.content:
            raise AnalizadorNoDisponible("Claude devolvió respuesta vacía")
        bloque = response.content[0]
        if not hasattr(bloque, "text"):
            raise AnalizadorNoDisponible(
                f"Bloque inesperado de Claude: {type(bloque).__name__}"
            )
        return bloque.text

    @staticmethod
    def _detectar_media_type(imagen_bytes: bytes) -> str:
        """Detecta JPEG/PNG/GIF/WebP por magic bytes (Claude rechaza si el mime no coincide)."""
        if imagen_bytes.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if imagen_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if imagen_bytes.startswith(b"GIF87a") or imagen_bytes.startswith(b"GIF89a"):
            return "image/gif"
        if imagen_bytes[:4] == b"RIFF" and imagen_bytes[8:12] == b"WEBP":
            return "image/webp"
        return "image/jpeg"  # fallback razonable (el ESP32 manda JPEG)

    @staticmethod
    def _extraer_json(texto: str) -> dict:
        """Claude a veces envuelve el JSON en texto. Extraemos el primer objeto balanceado."""
        inicio = texto.find("{")
        fin = texto.rfind("}")
        if inicio == -1 or fin == -1 or fin < inicio:
            raise ValueError(f"No se encontró objeto JSON en: {texto[:200]!r}")
        return json.loads(texto[inicio : fin + 1])

    @staticmethod
    def _mapear(data: dict) -> AnalisisImagen:
        detecciones = [
            Deteccion(
                nombre=str(p["nombre"]),
                cantidad=int(p["cantidad"]),
                confianza=Confianza(float(p["confianza"])),
            )
            for p in data.get("productos_detectados", [])
        ]
        return AnalisisImagen(
            detecciones=detecciones,
            cantidad_total=int(data.get("cantidad_total", 0)),
            espacios_vacios=bool(data.get("espacios_vacios", False)),
            confianza_general=Confianza(float(data.get("confianza_general", 0))),
            observaciones=str(data.get("observaciones", "")),
        )