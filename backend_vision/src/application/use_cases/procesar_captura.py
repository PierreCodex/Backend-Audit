"""Caso de uso único del backend Python: analizar y reenviar al POS."""
import base64

from application.dtos.captura_command import CapturaCommand
from application.dtos.resultado_captura import ResultadoCaptura
from application.ports.analizador_imagen import IAnalizadorImagen
from application.ports.pos_client import IPOSClient


class ProcesarCaptura:
    def __init__(self, analizador: IAnalizadorImagen, pos: IPOSClient) -> None:
        self._analizador = analizador
        self._pos = pos

    async def ejecutar(self, cmd: CapturaCommand) -> ResultadoCaptura:
        analisis = await self._analizador.analizar(cmd.imagen_bytes)

        imagen_b64 = base64.standard_b64encode(cmd.imagen_bytes).decode("ascii")

        respuesta_pos = await self._pos.notificar_auditoria(
            nodo_id=cmd.nodo_id.valor,
            imagen_base64=imagen_b64,
            timestamp_captura=cmd.timestamp,
            respuesta_ia=analisis.to_payload_pos(),
            tipo_evento=cmd.tipo_evento,
            request_id=cmd.request_id,
        )

        return ResultadoCaptura(analisis=analisis, respuesta_pos=respuesta_pos)