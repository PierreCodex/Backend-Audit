"""Endpoint principal: recibe imagen del ESP32 y delega al caso de uso."""
from datetime import datetime

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status

from application.dtos.captura_command import CapturaCommand
from application.use_cases.procesar_captura import ProcesarCaptura
from domain.value_objects.nodo_id import NodoId
from infrastructure.debug.capturas_storage import guardar_captura_debug
from interfaces.api.dependencies import get_procesar_captura
from interfaces.api.security import verificar_token_esp32
from interfaces.api.v1.schemas.captura import CapturaResponse
from shared.config import Settings, get_settings
from shared.logger import get_logger

log = get_logger(__name__)

router = APIRouter(
    prefix="/auditoria",
    tags=["auditoria"],
    dependencies=[Depends(verificar_token_esp32)],
)


@router.post(
    "/captura",
    response_model=CapturaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Recibe una imagen del ESP32 y la procesa con Claude → POS",
)
async def captura(
    imagen: UploadFile = File(..., description="Imagen JPEG capturada por el ESP32-S3-CAM"),
    nodo_id: str = Header(..., alias="X-Nodo-Id", description="MAC del ESP32 emisor"),
    timestamp: datetime = Header(
        ...,
        alias="X-Timestamp",
        description="ISO 8601 con timezone (ej. 2026-05-23T14:32:11-05:00)",
    ),
    tipo_evento: str = Header(
        "rutina",
        alias="X-Tipo-Evento",
        description="auditoria_apertura | rutina | reposicion | discrepancia",
    ),
    request_id: str | None = Header(
        None,
        alias="X-Request-Id",
        description="UUID opcional para idempotencia del POS",
    ),
    use_case: ProcesarCaptura = Depends(get_procesar_captura),
    settings: Settings = Depends(get_settings),
) -> CapturaResponse:
    imagen_bytes = await imagen.read()
    if not imagen_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La imagen está vacía",
        )

    cmd = CapturaCommand(
        imagen_bytes=imagen_bytes,
        nodo_id=NodoId(nodo_id),
        timestamp=timestamp,
        tipo_evento=tipo_evento,
        request_id=request_id,
    )

    log.info(
        "captura_recibida",
        nodo_id=nodo_id,
        timestamp=timestamp.isoformat(),
        tipo_evento=tipo_evento,
        request_id=request_id,
        bytes=len(imagen_bytes),
    )

    if settings.debug_guardar_capturas:
        try:
            guardar_captura_debug(
                storage_path=settings.storage_path,
                imagen_bytes=imagen_bytes,
                nodo_id=nodo_id,
                correlation_id=request_id or "no-corr-id",
                timestamp_iso=timestamp.isoformat(),
            )
        except Exception as e:
            log.warning("debug_guardar_fallo", error=str(e))

    # Control de costos: si el análisis automático está apagado, guardamos la imagen
    # (arriba) pero NO llamamos a Claude ni al POS. El ESP32 recibe 201 igual (LED
    # verde, sin reintentos). Para analizar después: `python ver_conteo.py <imagen>`.
    if not settings.analisis_automatico:
        log.info("captura_solo_guardada_sin_analisis", nodo_id=nodo_id, request_id=request_id)
        return CapturaResponse(
            auditoria_id_pos=0,
            accion_tomada="solo_guardada_sin_analisis",
            cantidad_total=0,
            confianza_general=0.0,
            espacios_vacios=False,
            idempotent_replay=False,
        )

    resultado = await use_case.ejecutar(cmd)

    log.info(
        "captura_procesada",
        nodo_id=nodo_id,
        auditoria_id_pos=resultado.respuesta_pos.auditoria_id,
        accion_tomada=resultado.respuesta_pos.accion_tomada,
        idempotent_replay=resultado.respuesta_pos.idempotent_replay,
    )

    return CapturaResponse(
        auditoria_id_pos=resultado.respuesta_pos.auditoria_id,
        accion_tomada=resultado.respuesta_pos.accion_tomada,
        cantidad_total=resultado.analisis.cantidad_total,
        confianza_general=resultado.analisis.confianza_general.valor,
        espacios_vacios=resultado.analisis.espacios_vacios,
        idempotent_replay=resultado.respuesta_pos.idempotent_replay,
    )