"""Caso de uso ProcesarCaptura: orquesta analizador + POS."""
from datetime import datetime, timezone

import pytest

from application.dtos.captura_command import CapturaCommand
from application.use_cases.procesar_captura import ProcesarCaptura
from domain.entities.analisis_imagen import AnalisisImagen
from domain.value_objects.nodo_id import NodoId
from infrastructure.pos.mock_pos_client import MockPOSClient


class FakeAnalizador:
    """Devuelve siempre el mismo AnalisisImagen, registra cuántas veces se llamó."""

    def __init__(self, analisis: AnalisisImagen):
        self._analisis = analisis
        self.llamadas: list[bytes] = []

    async def analizar(self, imagen_bytes: bytes) -> AnalisisImagen:
        self.llamadas.append(imagen_bytes)
        return self._analisis


@pytest.mark.asyncio
async def test_procesar_captura_orquesta_analizador_y_pos(analisis_fake, imagen_bytes_dummy):
    analizador = FakeAnalizador(analisis_fake)
    pos = MockPOSClient()
    use_case = ProcesarCaptura(analizador=analizador, pos=pos)

    cmd = CapturaCommand(
        imagen_bytes=imagen_bytes_dummy,
        nodo_id=NodoId("14:c1:9f:c1:b7:60"),
        timestamp=datetime.now(timezone.utc),
        tipo_evento="rutina",
        request_id="req-test-1",
    )

    resultado = await use_case.ejecutar(cmd)

    assert len(analizador.llamadas) == 1
    assert analizador.llamadas[0] == imagen_bytes_dummy

    assert len(pos.llamadas) == 1
    llamada = pos.llamadas[0]
    assert llamada["nodo_id"] == "14:c1:9f:c1:b7:60"
    assert llamada["tipo_evento"] == "rutina"
    assert llamada["request_id"] == "req-test-1"

    payload_ia = llamada["respuesta_ia"]
    assert payload_ia["cantidad_total"] == 7
    assert payload_ia["confianza_general"] == 0.93
    assert payload_ia["espacios_vacios"] is False
    assert len(payload_ia["productos_detectados"]) == 2
    assert payload_ia["productos_detectados"][0] == {
        "nombre": "Coca-Cola 1.5L",
        "cantidad": 4,
        "confianza": 0.95,
    }

    assert resultado.analisis == analisis_fake
    assert resultado.respuesta_pos.auditoria_id == 1
    assert resultado.respuesta_pos.accion_tomada == "validada_venta"
    assert resultado.respuesta_pos.idempotent_replay is False


@pytest.mark.asyncio
async def test_idempotencia_mismo_request_id_reusa_respuesta(analisis_fake, imagen_bytes_dummy):
    analizador = FakeAnalizador(analisis_fake)
    pos = MockPOSClient()
    use_case = ProcesarCaptura(analizador=analizador, pos=pos)

    cmd = CapturaCommand(
        imagen_bytes=imagen_bytes_dummy,
        nodo_id=NodoId("14:c1:9f:c1:b7:60"),
        timestamp=datetime.now(timezone.utc),
        request_id="req-duplicado",
    )

    primero = await use_case.ejecutar(cmd)
    segundo = await use_case.ejecutar(cmd)

    assert primero.respuesta_pos.auditoria_id == segundo.respuesta_pos.auditoria_id
    assert segundo.respuesta_pos.idempotent_replay is True
    assert len([c for c in pos.llamadas if c["request_id"] == "req-duplicado"]) == 1


@pytest.mark.asyncio
async def test_imagen_se_codifica_a_base64_para_el_pos(analisis_fake):
    analizador = FakeAnalizador(analisis_fake)
    pos = MockPOSClient()
    use_case = ProcesarCaptura(analizador=analizador, pos=pos)

    # 100 bytes arbitrarios → en base64 son 136 caracteres aprox
    imagen = b"\x00" * 100

    cmd = CapturaCommand(
        imagen_bytes=imagen,
        nodo_id=NodoId("14:c1:9f:c1:b7:60"),
        timestamp=datetime.now(timezone.utc),
    )
    await use_case.ejecutar(cmd)

    # base64 de 100 bytes = ceil(100/3)*4 = 136 caracteres
    assert pos.llamadas[0]["imagen_bytes_b64_len"] == 136