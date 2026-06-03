"""Tests de la API HTTP del backend con dependencias inyectadas."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from application.use_cases.procesar_captura import ProcesarCaptura
from domain.entities.analisis_imagen import AnalisisImagen
from domain.entities.deteccion import Deteccion
from domain.value_objects.confianza import Confianza
from infrastructure.pos.mock_pos_client import MockPOSClient
from interfaces.api.dependencies import get_procesar_captura
from main import app


class _AnalizadorFake:
    def __init__(self, analisis: AnalisisImagen):
        self._analisis = analisis

    async def analizar(self, imagen_bytes: bytes) -> AnalisisImagen:
        return self._analisis


@pytest.fixture
def analisis_demo() -> AnalisisImagen:
    return AnalisisImagen(
        detecciones=[
            Deteccion(nombre="Coca-Cola 1.5L", cantidad=4, confianza=Confianza(0.95)),
        ],
        cantidad_total=4,
        espacios_vacios=True,
        confianza_general=Confianza(0.9),
    )


@pytest.fixture
def cliente(analisis_demo):
    pos = MockPOSClient()
    analizador = _AnalizadorFake(analisis_demo)

    def _override():
        return ProcesarCaptura(analizador=analizador, pos=pos)

    app.dependency_overrides[get_procesar_captura] = _override
    with TestClient(app) as c:
        c.pos = pos  # type: ignore[attr-defined]
        yield c
    app.dependency_overrides.clear()


def test_health_no_requiere_auth(cliente):
    res = cliente.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_captura_sin_token_rechaza_401(cliente, imagen_bytes_dummy):
    res = cliente.post(
        "/api/v1/auditoria/captura",
        files={"imagen": ("foto.jpg", imagen_bytes_dummy, "image/jpeg")},
        headers={
            "X-Nodo-Id": "14:c1:9f:c1:b7:60",
            "X-Timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert res.status_code == 401


def test_captura_con_token_invalido_rechaza_401(cliente, imagen_bytes_dummy):
    res = cliente.post(
        "/api/v1/auditoria/captura",
        files={"imagen": ("foto.jpg", imagen_bytes_dummy, "image/jpeg")},
        headers={
            "Authorization": "Bearer token-malo",
            "X-Nodo-Id": "14:c1:9f:c1:b7:60",
            "X-Timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert res.status_code == 401


def test_captura_exitosa_devuelve_201_y_llama_al_pos(cliente, imagen_bytes_dummy):
    res = cliente.post(
        "/api/v1/auditoria/captura",
        files={"imagen": ("foto.jpg", imagen_bytes_dummy, "image/jpeg")},
        headers={
            "Authorization": "Bearer esp32-test-token",
            "X-Nodo-Id": "14:c1:9f:c1:b7:60",
            "X-Timestamp": datetime.now(timezone.utc).isoformat(),
            "X-Tipo-Evento": "rutina",
            "X-Request-Id": "req-int-1",
        },
    )

    assert res.status_code == 201, res.text
    data = res.json()
    assert data["accion_tomada"] == "validada_venta"
    assert data["cantidad_total"] == 4
    assert data["confianza_general"] == 0.9
    assert data["espacios_vacios"] is True
    assert data["idempotent_replay"] is False
    assert data["auditoria_id_pos"] == 1

    # Verificar lo que llegó al POS
    llamadas = cliente.pos.llamadas  # type: ignore[attr-defined]
    assert len(llamadas) == 1
    assert llamadas[0]["nodo_id"] == "14:c1:9f:c1:b7:60"
    assert llamadas[0]["request_id"] == "req-int-1"
    assert llamadas[0]["respuesta_ia"]["cantidad_total"] == 4


def test_imagen_vacia_devuelve_400(cliente):
    res = cliente.post(
        "/api/v1/auditoria/captura",
        files={"imagen": ("foto.jpg", b"", "image/jpeg")},
        headers={
            "Authorization": "Bearer esp32-test-token",
            "X-Nodo-Id": "14:c1:9f:c1:b7:60",
            "X-Timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert res.status_code == 400


def test_nodo_id_invalido_devuelve_422(cliente, imagen_bytes_dummy):
    res = cliente.post(
        "/api/v1/auditoria/captura",
        files={"imagen": ("foto.jpg", imagen_bytes_dummy, "image/jpeg")},
        headers={
            "Authorization": "Bearer esp32-test-token",
            "X-Nodo-Id": "abc",  # muy corto, rompe invariante de NodoId
            "X-Timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert res.status_code == 422
    assert "valor_invalido" in res.text or "NodoId" in res.text