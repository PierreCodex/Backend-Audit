"""Wiring de Dependency Injection. Único lugar donde se instancia infraestructura concreta."""
from functools import lru_cache

from anthropic import AsyncAnthropic
from fastapi import Depends

from application.ports.pos_client import IPOSClient
from application.use_cases.procesar_captura import ProcesarCaptura
from infrastructure.ia.claude_analizador import ClaudeAnalizador
from infrastructure.pos.laravel_pos_client import LaravelPOSClient
from infrastructure.pos.mock_pos_client import MockPOSClient
from shared.config import Settings, get_settings


@lru_cache
def get_anthropic_client() -> AsyncAnthropic:
    """Cliente Anthropic singleton (manejo de conexiones HTTP interno del SDK)."""
    settings = get_settings()
    return AsyncAnthropic(api_key=settings.anthropic_api_key)


def get_analizador(
    client: AsyncAnthropic = Depends(get_anthropic_client),
    settings: Settings = Depends(get_settings),
) -> ClaudeAnalizador:
    return ClaudeAnalizador(client=client, modelo=settings.claude_model)


@lru_cache
def _build_pos_client() -> IPOSClient:
    """Singleton del cliente POS. LaravelPOSClient mantiene conexión httpx persistente."""
    settings = get_settings()
    if settings.use_mock_pos:
        return MockPOSClient()
    return LaravelPOSClient(base_url=settings.pos_url, token=settings.pos_token)


def get_pos_client() -> IPOSClient:
    return _build_pos_client()


def get_procesar_captura(
    analizador: ClaudeAnalizador = Depends(get_analizador),
    pos: IPOSClient = Depends(get_pos_client),
) -> ProcesarCaptura:
    return ProcesarCaptura(analizador=analizador, pos=pos)