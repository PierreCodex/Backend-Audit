"""Fixtures comunes y configuración de env para tests."""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-fake")
os.environ.setdefault("ESP32_API_TOKEN", "esp32-test-token")
os.environ.setdefault("POS_URL", "http://localhost/test")
os.environ.setdefault("POS_TOKEN", "pos-test-token")
os.environ.setdefault("USE_MOCK_POS", "true")
os.environ.setdefault("CLAUDE_MODEL", "claude-sonnet-4-6")

import pytest

from domain.entities.analisis_imagen import AnalisisImagen
from domain.entities.deteccion import Deteccion
from domain.value_objects.confianza import Confianza


@pytest.fixture
def analisis_fake() -> AnalisisImagen:
    return AnalisisImagen(
        detecciones=[
            Deteccion(nombre="Coca-Cola 1.5L", cantidad=4, confianza=Confianza(0.95)),
            Deteccion(nombre="Inca Kola 1.5L", cantidad=3, confianza=Confianza(0.92)),
        ],
        cantidad_total=7,
        espacios_vacios=False,
        confianza_general=Confianza(0.93),
        observaciones="Estante ordenado",
    )


@pytest.fixture
def imagen_bytes_dummy() -> bytes:
    # JPEG mínimo válido (start of image + end of image)
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"