"""Configuración centralizada via pydantic-settings (.env)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # IA
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-6"

    # POS Laravel (local en desarrollo, Railway en producción)
    pos_url: str = "http://localhost/SistemaPosV2/public"
    pos_token: str = ""
    use_mock_pos: bool = False

    # Auth ESP32 → backend Python
    esp32_api_token: str

    # Servidor
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Umbrales de negocio
    confianza_minima: float = 0.70

    # Debug (no usar en producción)
    debug_guardar_capturas: bool = False
    storage_path: str = "./storage"

    # Control de costos: si es False, el backend GUARDA la imagen pero NO la manda
    # a Claude (no gasta tokens). Sirve para pruebas con el ESP32 capturando basura.
    # El ESP32 igual recibe 201. Luego se analiza manual con `python ver_conteo.py`.
    analisis_automatico: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()