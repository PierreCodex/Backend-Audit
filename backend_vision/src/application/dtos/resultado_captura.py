from dataclasses import dataclass

from domain.entities.analisis_imagen import AnalisisImagen


@dataclass(frozen=True)
class RespuestaPOS:
    """Lo que devuelve el POS Laravel tras procesar la auditoría."""

    auditoria_id: int
    accion_tomada: str  # pendiente | validada_venta | merma_sospechosa | reposicion_confirmada
    idempotent_replay: bool = False


@dataclass(frozen=True)
class ResultadoCaptura:
    """Salida del caso de uso ProcesarCaptura."""

    analisis: AnalisisImagen
    respuesta_pos: RespuestaPOS