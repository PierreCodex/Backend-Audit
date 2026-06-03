"""Tests de la entidad AnalisisImagen y su serialización al contrato del POS."""
from domain.entities.analisis_imagen import AnalisisImagen
from domain.entities.deteccion import Deteccion
from domain.value_objects.confianza import Confianza


def test_to_payload_pos_coincide_con_contrato_de_storeauditoriavisualrequest():
    """El payload debe coincidir EXACTAMENTE con StoreAuditoriaVisualRequest.php del POS."""
    analisis = AnalisisImagen(
        detecciones=[
            Deteccion(nombre="Coca-Cola 500ml", cantidad=2, confianza=Confianza(0.94)),
            Deteccion(nombre="Inca Kola 500ml", cantidad=2, confianza=Confianza(0.91)),
        ],
        cantidad_total=4,
        espacios_vacios=False,
        confianza_general=Confianza(0.92),
    )

    payload = analisis.to_payload_pos()

    # Estructura exacta esperada por el POS (sección respuesta_ia del FormRequest)
    assert set(payload.keys()) == {
        "cantidad_total",
        "espacios_vacios",
        "confianza_general",
        "productos_detectados",
    }
    assert payload["cantidad_total"] == 4
    assert payload["espacios_vacios"] is False
    assert payload["confianza_general"] == 0.92
    assert payload["productos_detectados"] == [
        {"nombre": "Coca-Cola 500ml", "cantidad": 2, "confianza": 0.94},
        {"nombre": "Inca Kola 500ml", "cantidad": 2, "confianza": 0.91},
    ]


def test_payload_acepta_estante_vacio():
    analisis = AnalisisImagen(
        detecciones=[],
        cantidad_total=0,
        espacios_vacios=True,
        confianza_general=Confianza(0.85),
    )
    payload = analisis.to_payload_pos()
    assert payload["productos_detectados"] == []
    assert payload["cantidad_total"] == 0