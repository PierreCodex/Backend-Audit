"""Validación del Bearer token que el ESP32 incluye en cada captura."""
from fastapi import Depends, Header, HTTPException, status

from shared.config import Settings, get_settings


def verificar_token_esp32(
    authorization: str | None = Header(default=None, description="Bearer <ESP32_API_TOKEN>"),
    settings: Settings = Depends(get_settings),
) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token requerido (formato: Bearer <token>)",
        )
    token = authorization.removeprefix("Bearer ").strip()
    if not token or token != settings.esp32_api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )