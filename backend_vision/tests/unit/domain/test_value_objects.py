"""Tests de invariantes en value objects de dominio."""
from datetime import datetime, timedelta, timezone

import pytest

from domain.value_objects.confianza import Confianza
from domain.value_objects.nodo_id import NodoId
from domain.value_objects.timestamp_captura import TimestampCaptura


class TestNodoId:
    def test_valido(self):
        nodo = NodoId("14:c1:9f:c1:b7:60")
        assert nodo.valor == "14:c1:9f:c1:b7:60"

    @pytest.mark.parametrize("invalido", ["", "abc", "12345"])
    def test_rechaza_invalidos(self, invalido):
        with pytest.raises(ValueError):
            NodoId(invalido)


class TestConfianza:
    @pytest.mark.parametrize("valor", [0.0, 0.5, 0.93, 1.0])
    def test_acepta_rango_valido(self, valor):
        c = Confianza(valor)
        assert c.valor == valor

    @pytest.mark.parametrize("invalido", [-0.1, 1.01, 2.0, -5])
    def test_rechaza_fuera_de_rango(self, invalido):
        with pytest.raises(ValueError):
            Confianza(invalido)

    def test_es_aceptable(self):
        assert Confianza(0.8).es_aceptable(0.7) is True
        assert Confianza(0.6).es_aceptable(0.7) is False


class TestTimestampCaptura:
    def test_requiere_timezone(self):
        with pytest.raises(ValueError, match="timezone"):
            TimestampCaptura(datetime(2026, 5, 23, 14, 30, 0))  # naive

    def test_rechaza_futuro(self):
        futuro = datetime.now(timezone.utc) + timedelta(days=1)
        with pytest.raises(ValueError, match="futuro"):
            TimestampCaptura(futuro)

    def test_acepta_presente_con_tz(self):
        ahora = datetime.now(timezone.utc)
        ts = TimestampCaptura(ahora)
        assert ts.to_iso() == ahora.isoformat()