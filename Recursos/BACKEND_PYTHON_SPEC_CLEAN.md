# Especificación del Backend Python (Clean Architecture, stateless) — Sistema de Auditoría Visual de Inventario

Documento de referencia para Claude Code. Versión **simplificada y alineada al POS Laravel real** (`C:\xampp\htdocs\SistemaPosV2`), aplicando **Clean Architecture** (Uncle Bob) y las mejores prácticas de FastAPI (validadas con docs oficiales vía Context7).

## Cambios respecto a versiones anteriores

Tras revisar el POS Laravel ya implementado (`SistemaPosV2`, plan `plan_implementacion_vision.md`), confirmamos que el POS clasifica internamente venta/merma/reposición consultando su propia BD MySQL. Por lo tanto el backend Python queda **stateless**: sin BD propia, sin clasificación duplicada, sin storage local de imágenes. Solo orquesta:

```
ESP32 → recibe imagen → Claude analiza → POST al POS → devuelve respuesta
```

Nada se persiste en Python. La fuente única de verdad es el POS.

---

## 1. Contexto del proyecto

Sistema IoT de auditoría visual de inventario para tienda minorista en Piura, Perú. Proyecto académico universitario.

Flujo:
```
ESP32-S3-CAM  →  Backend Python (FastAPI, stateless)  →  POS Laravel (Railway)
  (captura)         (ESTE PROYECTO)                        │  ↳ clasifica + guarda
                          │                                ↓
                          ↓                          WhatsApp (Twilio)
                   API Claude Sonnet 4.6
```

Hardware del nodo: ESP32-S3 N16R8 CAM con OV3660, MAC `14:c1:9f:c1:b7:60`, JPEG SVGA 800x600 (ver `HARDWARE_ESP32_CONFIG.md`).

---

## 2. Principios de arquitectura

### Regla de Dependencia
Las dependencias **siempre apuntan hacia adentro**:

```
interfaces  →  application  →  domain
                    ↑
            infrastructure
        (implementa puertos definidos en application)
```

- **`domain/`** no importa NADA de las otras capas. Sin FastAPI, sin Pydantic, sin Anthropic, sin httpx.
- **`application/`** define *puertos* (Protocols) e implementa *casos de uso*. Solo conoce `domain`.
- **`infrastructure/`** implementa los puertos con tecnologías concretas (Claude SDK, httpx).
- **`interfaces/`** expone FastAPI, hace el *wiring* con DI, traduce HTTP ↔ DTOs.

### Reglas duras
1. Si un archivo de `domain/` importa `fastapi`, `anthropic`, `httpx` o `cv2`: bug arquitectónico.
2. Si un caso de uso instancia directamente `AsyncClient()` o `Anthropic()`: bug arquitectónico.
3. Toda dependencia externa entra a un caso de uso por su constructor, tipada con un Protocol.

---

## 3. Stack tecnológico

- **Lenguaje:** Python 3.11+
- **Framework:** FastAPI
- **Servidor ASGI:** Uvicorn
- **Configuración:** `pydantic-settings` (BaseSettings con `.env`)
- **Cliente HTTP async:** httpx
- **API IA:** anthropic (SDK oficial)
- **Validación / DTOs HTTP:** Pydantic v2
- **Logging:** structlog (logs estructurados con correlation IDs hacia stdout — Railway los captura)
- **Tests:** pytest + pytest-asyncio + httpx (`AsyncClient`)
- **Modelo Claude:** `claude-sonnet-4-6`

**No usa:** base de datos, ORM, migraciones, file storage persistente. Python es un servicio sin estado.

---

## 4. Estructura de carpetas

```
backend_vision/
├── pyproject.toml
├── requirements.txt
├── .env.example
├── .env                              # NO commitear
├── README.md
├── Dockerfile
│
├── src/
│   ├── __init__.py
│   ├── main.py                       # entrypoint FastAPI
│   │
│   ├── domain/                       # CAPA 1 — núcleo, sin dependencias externas
│   │   ├── __init__.py
│   │   ├── entities/
│   │   │   ├── __init__.py
│   │   │   ├── deteccion.py          # un producto detectado por Claude
│   │   │   └── analisis_imagen.py    # respuesta completa de Claude
│   │   ├── value_objects/
│   │   │   ├── __init__.py
│   │   │   ├── nodo_id.py
│   │   │   ├── confianza.py
│   │   │   └── timestamp_captura.py
│   │   └── exceptions.py             # DomainError, ConfianzaInsuficiente, CapturaInvalida
│   │
│   ├── application/                  # CAPA 2 — orquestación
│   │   ├── __init__.py
│   │   ├── ports/                    # interfaces (Protocols)
│   │   │   ├── __init__.py
│   │   │   ├── analizador_imagen.py  # IAnalizadorImagen
│   │   │   └── pos_client.py         # IPOSClient
│   │   ├── use_cases/
│   │   │   ├── __init__.py
│   │   │   └── procesar_captura.py
│   │   └── dtos/
│   │       ├── __init__.py
│   │       ├── captura_command.py
│   │       └── resultado_captura.py
│   │
│   ├── infrastructure/               # CAPA 3 — adaptadores concretos
│   │   ├── __init__.py
│   │   ├── ia/
│   │   │   ├── __init__.py
│   │   │   ├── claude_analizador.py  # implementa IAnalizadorImagen
│   │   │   └── prompts.py
│   │   └── pos/
│   │       ├── __init__.py
│   │       ├── laravel_pos_client.py # implementa IPOSClient
│   │       └── mock_pos_client.py    # fake para tests / desarrollo offline
│   │
│   ├── interfaces/                   # CAPA 4 — entrada HTTP
│   │   ├── __init__.py
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── v1/
│   │       │   ├── __init__.py
│   │       │   ├── routers/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── auditoria.py
│   │       │   │   └── health.py
│   │       │   └── schemas/
│   │       │       ├── __init__.py
│   │       │       ├── captura.py
│   │       │       └── respuesta.py
│   │       ├── dependencies.py       # wiring con Depends()
│   │       ├── exception_handlers.py
│   │       ├── middleware.py         # correlation_id, logging
│   │       └── security.py           # auth Bearer del ESP32
│   │
│   └── shared/
│       ├── __init__.py
│       ├── config.py                 # Settings(BaseSettings)
│       └── logger.py                 # structlog
│
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── unit/
    │   └── application/
    │       └── test_procesar_captura.py    # con fakes de puertos
    ├── integration/
    │   └── test_api_captura.py             # FastAPI TestClient + MockPOSClient
    └── fixtures/
        └── imagenes/
            ├── estante_lleno.jpg
            └── estante_con_merma.jpg
```

**No hay**: `storage/`, `migrations/`, `infrastructure/persistence/`, `infrastructure/image_processing/`, `infrastructure/notificacion/`. Eliminados porque la responsabilidad vive en el POS.

---

## 5. Detalle de cada capa

### 5.1 `domain/` — Núcleo del negocio

**Reglas:**
- Solo `dataclasses`, `enum`, `typing`, `datetime`. Nunca `pydantic`, `fastapi`, `anthropic`.
- Las entidades son `@dataclass(frozen=True)` con invariantes en `__post_init__`.

`domain/value_objects/nodo_id.py`
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class NodoId:
    valor: str

    def __post_init__(self):
        if not self.valor or len(self.valor) < 12:
            raise ValueError("NodoId inválido")
```

`domain/value_objects/confianza.py`
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Confianza:
    """Confianza en escala 0.0–1.0 (igual a lo que devuelve Claude y espera el POS)."""
    valor: float

    def __post_init__(self):
        if not (0.0 <= self.valor <= 1.0):
            raise ValueError(f"Confianza debe estar entre 0 y 1, recibido {self.valor}")

    def es_aceptable(self, umbral: float) -> bool:
        return self.valor >= umbral
```

`domain/entities/deteccion.py`
```python
from dataclasses import dataclass
from domain.value_objects.confianza import Confianza

@dataclass(frozen=True)
class Deteccion:
    nombre: str
    cantidad: int
    confianza: Confianza

    def __post_init__(self):
        if self.cantidad < 0:
            raise ValueError("cantidad no puede ser negativa")
        if not self.nombre.strip():
            raise ValueError("nombre no puede estar vacío")
```

`domain/entities/analisis_imagen.py`
```python
from dataclasses import dataclass
from domain.entities.deteccion import Deteccion
from domain.value_objects.confianza import Confianza

@dataclass(frozen=True)
class AnalisisImagen:
    detecciones: list[Deteccion]
    cantidad_total: int
    espacios_vacios: bool
    confianza_general: Confianza
    observaciones: str = ""

    def to_payload_pos(self) -> dict:
        """Serializa exactamente al contrato que espera el POS Laravel."""
        return {
            "cantidad_total": self.cantidad_total,
            "espacios_vacios": self.espacios_vacios,
            "confianza_general": self.confianza_general.valor,
            "productos_detectados": [
                {
                    "nombre": d.nombre,
                    "cantidad": d.cantidad,
                    "confianza": d.confianza.valor,
                }
                for d in self.detecciones
            ],
        }
```

`domain/exceptions.py`
```python
class DomainError(Exception): ...
class ConfianzaInsuficiente(DomainError): ...
class CapturaInvalida(DomainError): ...
class POSNoDisponible(DomainError): ...
class AnalizadorNoDisponible(DomainError): ...
```

---

### 5.2 `application/` — Puertos y caso de uso único

**`ports/analizador_imagen.py`**
```python
from typing import Protocol
from domain.entities.analisis_imagen import AnalisisImagen

class IAnalizadorImagen(Protocol):
    async def analizar(self, imagen_bytes: bytes) -> AnalisisImagen: ...
```

**`ports/pos_client.py`** — solo UN método (alineado al endpoint real `POST /api/vision/auditoria/registrar`):
```python
from typing import Protocol
from datetime import datetime
from application.dtos.resultado_captura import RespuestaPOS

class IPOSClient(Protocol):
    async def notificar_auditoria(
        self,
        nodo_id: str,
        imagen_base64: str,
        timestamp_captura: datetime,
        respuesta_ia: dict,
        tipo_evento: str = "rutina",
    ) -> RespuestaPOS: ...
```

**`dtos/captura_command.py`**
```python
from dataclasses import dataclass
from datetime import datetime
from domain.value_objects.nodo_id import NodoId

@dataclass(frozen=True)
class CapturaCommand:
    imagen_bytes: bytes
    nodo_id: NodoId
    timestamp: datetime
    tipo_evento: str = "rutina"
```

**`dtos/resultado_captura.py`**
```python
from dataclasses import dataclass
from domain.entities.analisis_imagen import AnalisisImagen

@dataclass(frozen=True)
class RespuestaPOS:
    auditoria_id: int
    accion_tomada: str   # pendiente | validada_venta | merma_sospechosa | reposicion_confirmada

@dataclass(frozen=True)
class ResultadoCaptura:
    analisis: AnalisisImagen
    respuesta_pos: RespuestaPOS
```

**`use_cases/procesar_captura.py`** — el corazón, ahora trivial:
```python
import base64
from application.ports.analizador_imagen import IAnalizadorImagen
from application.ports.pos_client import IPOSClient
from application.dtos.captura_command import CapturaCommand
from application.dtos.resultado_captura import ResultadoCaptura

class ProcesarCaptura:
    def __init__(self, analizador: IAnalizadorImagen, pos: IPOSClient):
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
        )

        return ResultadoCaptura(analisis=analisis, respuesta_pos=respuesta_pos)
```

**Observa:** este caso de uso no sabe nada de Claude, ni de httpx, ni de FastAPI. Es testeable con dos fakes.

---

### 5.3 `infrastructure/` — Adaptadores concretos

#### `infrastructure/ia/claude_analizador.py`
```python
import json
from anthropic import AsyncAnthropic
from application.ports.analizador_imagen import IAnalizadorImagen
from domain.entities.analisis_imagen import AnalisisImagen
from domain.entities.deteccion import Deteccion
from domain.value_objects.confianza import Confianza
from domain.exceptions import AnalizadorNoDisponible
from infrastructure.ia.prompts import PROMPT_AUDITORIA

class ClaudeAnalizador(IAnalizadorImagen):
    def __init__(self, client: AsyncAnthropic, modelo: str):
        self._client = client
        self._modelo = modelo

    async def analizar(self, imagen_bytes: bytes) -> AnalisisImagen:
        import base64
        b64 = base64.standard_b64encode(imagen_bytes).decode()
        try:
            response = await self._client.messages.create(
                model=self._modelo,
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                        {"type": "text", "text": PROMPT_AUDITORIA},
                    ],
                }],
            )
        except Exception as e:
            raise AnalizadorNoDisponible(f"Fallo al llamar Claude: {e}") from e

        raw = response.content[0].text
        data = self._extraer_json(raw)
        return self._mapear(data)

    @staticmethod
    def _extraer_json(texto: str) -> dict:
        inicio = texto.find("{")
        fin = texto.rfind("}")
        return json.loads(texto[inicio:fin + 1])

    @staticmethod
    def _mapear(data: dict) -> AnalisisImagen:
        detecciones = [
            Deteccion(
                nombre=p["nombre"],
                cantidad=int(p["cantidad"]),
                confianza=Confianza(float(p["confianza"])),
            )
            for p in data.get("productos_detectados", [])
        ]
        return AnalisisImagen(
            detecciones=detecciones,
            cantidad_total=int(data.get("cantidad_total", 0)),
            espacios_vacios=bool(data.get("espacios_vacios", False)),
            confianza_general=Confianza(float(data.get("confianza_general", 0))),
            observaciones=data.get("observaciones", ""),
        )
```

#### `infrastructure/ia/prompts.py`
```python
PROMPT_AUDITORIA = """
Eres un sistema de auditoría visual de inventario. Analiza esta imagen de un
estante de productos de una tienda. Identifica cada producto visible, cuenta
cuántas unidades hay de cada uno, e identifica si hay espacios vacíos.

Los productos esperados son gaseosas: Coca-Cola, Inca Kola, Pepsi, Fanta,
Sprite, en presentaciones de 500ml y 1.5L.

Responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional:
{
  "productos_detectados": [
    {"nombre": "Coca-Cola 1.5L", "cantidad": 4, "confianza": 0.95}
  ],
  "cantidad_total": 7,
  "espacios_vacios": true,
  "confianza_general": 0.93,
  "observaciones": "..."
}

Las confianzas van de 0 a 1.
""".strip()
```

#### `infrastructure/pos/laravel_pos_client.py`
```python
from datetime import datetime
import httpx
from application.ports.pos_client import IPOSClient
from application.dtos.resultado_captura import RespuestaPOS
from domain.exceptions import POSNoDisponible

class LaravelPOSClient(IPOSClient):
    def __init__(self, base_url: str, token: str, timeout: float = 30.0):
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
        )

    async def notificar_auditoria(
        self,
        nodo_id: str,
        imagen_base64: str,
        timestamp_captura: datetime,
        respuesta_ia: dict,
        tipo_evento: str = "rutina",
    ) -> RespuestaPOS:
        payload = {
            "nodo_id": nodo_id,
            "imagen_base64": imagen_base64,
            "timestamp_captura": timestamp_captura.isoformat(),
            "tipo_evento": tipo_evento,
            "respuesta_ia": respuesta_ia,
        }
        try:
            res = await self._client.post("/api/vision/auditoria/registrar", json=payload)
            res.raise_for_status()
        except httpx.HTTPError as e:
            raise POSNoDisponible(f"POS rechazó la auditoría: {e}") from e

        data = res.json()
        return RespuestaPOS(
            auditoria_id=int(data["auditoria_id"]),
            accion_tomada=str(data["accion_tomada"]),
        )

    async def close(self):
        await self._client.aclose()
```

> **Nota sobre el contrato:** la estructura del payload (`nodo_id`, `imagen_base64`, `timestamp_captura`, `tipo_evento`, `respuesta_ia: {cantidad_total, espacios_vacios, confianza_general, productos_detectados[...]}`) está alineada exactamente con `StoreAuditoriaVisualRequest.php` del POS (`C:\xampp\htdocs\SistemaPosV2\app\Http\Requests\Vision\StoreAuditoriaVisualRequest.php`). NO MODIFICAR sin actualizar también el FormRequest del POS.

#### `infrastructure/pos/mock_pos_client.py`
```python
from datetime import datetime
from application.ports.pos_client import IPOSClient
from application.dtos.resultado_captura import RespuestaPOS

class MockPOSClient(IPOSClient):
    """POS falso para desarrollo offline y tests."""

    def __init__(self):
        self.llamadas: list[dict] = []
        self._next_id = 1

    async def notificar_auditoria(
        self,
        nodo_id: str,
        imagen_base64: str,
        timestamp_captura: datetime,
        respuesta_ia: dict,
        tipo_evento: str = "rutina",
    ) -> RespuestaPOS:
        self.llamadas.append({
            "nodo_id": nodo_id,
            "timestamp_captura": timestamp_captura,
            "tipo_evento": tipo_evento,
            "cantidad_total": respuesta_ia.get("cantidad_total"),
        })
        respuesta = RespuestaPOS(auditoria_id=self._next_id, accion_tomada="pendiente")
        self._next_id += 1
        return respuesta
```

---

### 5.4 `interfaces/` — FastAPI

#### `interfaces/api/dependencies.py` — único lugar de wiring
```python
from functools import lru_cache
from fastapi import Depends
from anthropic import AsyncAnthropic

from shared.config import Settings, get_settings
from application.use_cases.procesar_captura import ProcesarCaptura
from infrastructure.ia.claude_analizador import ClaudeAnalizador
from infrastructure.pos.laravel_pos_client import LaravelPOSClient
from infrastructure.pos.mock_pos_client import MockPOSClient

@lru_cache
def get_anthropic_client() -> AsyncAnthropic:
    return AsyncAnthropic(api_key=get_settings().anthropic_api_key)

def get_analizador(
    client: AsyncAnthropic = Depends(get_anthropic_client),
    settings: Settings = Depends(get_settings),
) -> ClaudeAnalizador:
    return ClaudeAnalizador(client, settings.claude_model)

@lru_cache
def get_pos_client_singleton() -> IPOSClient:
    s = get_settings()
    if s.use_mock_pos:
        return MockPOSClient()
    return LaravelPOSClient(base_url=s.pos_url, token=s.pos_token)

def get_pos_client():
    return get_pos_client_singleton()

def get_procesar_captura(
    analizador=Depends(get_analizador),
    pos=Depends(get_pos_client),
) -> ProcesarCaptura:
    return ProcesarCaptura(analizador, pos)
```

#### `interfaces/api/v1/routers/auditoria.py` — router delgado
```python
from fastapi import APIRouter, Depends, UploadFile, File, Header
from datetime import datetime

from application.use_cases.procesar_captura import ProcesarCaptura
from application.dtos.captura_command import CapturaCommand
from interfaces.api.dependencies import get_procesar_captura
from interfaces.api.security import verificar_token_esp32
from interfaces.api.v1.schemas.captura import CapturaResponse
from domain.value_objects.nodo_id import NodoId

router = APIRouter(
    prefix="/auditoria",
    tags=["auditoria"],
    dependencies=[Depends(verificar_token_esp32)],
)

@router.post("/captura", response_model=CapturaResponse, status_code=201)
async def captura(
    imagen: UploadFile = File(...),
    nodo_id: str = Header(..., alias="X-Nodo-Id"),
    timestamp: datetime = Header(..., alias="X-Timestamp"),
    tipo_evento: str = Header("rutina", alias="X-Tipo-Evento"),
    use_case: ProcesarCaptura = Depends(get_procesar_captura),
):
    cmd = CapturaCommand(
        imagen_bytes=await imagen.read(),
        nodo_id=NodoId(nodo_id),
        timestamp=timestamp,
        tipo_evento=tipo_evento,
    )
    resultado = await use_case.ejecutar(cmd)
    return CapturaResponse(
        auditoria_id_pos=resultado.respuesta_pos.auditoria_id,
        accion_tomada=resultado.respuesta_pos.accion_tomada,
        cantidad_total=resultado.analisis.cantidad_total,
        confianza_general=resultado.analisis.confianza_general.valor,
        espacios_vacios=resultado.analisis.espacios_vacios,
    )
```

#### `interfaces/api/v1/schemas/captura.py`
```python
from pydantic import BaseModel

class CapturaResponse(BaseModel):
    auditoria_id_pos: int
    accion_tomada: str
    cantidad_total: int
    confianza_general: float
    espacios_vacios: bool
```

#### `interfaces/api/security.py`
```python
from fastapi import Header, HTTPException, status, Depends
from shared.config import Settings, get_settings

def verificar_token_esp32(
    authorization: str = Header(...),
    settings: Settings = Depends(get_settings),
) -> None:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token requerido")
    token = authorization.removeprefix("Bearer ").strip()
    if token != settings.esp32_api_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")
```

---

### 5.5 `shared/config.py`
```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # IA
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-6"

    # POS Laravel (Railway)
    pos_url: str                       # https://tu-pos.up.railway.app
    pos_token: str                     # token Sanctum emitido por `php artisan integracion:generar-token-python`
    use_mock_pos: bool = False

    # Auth ESP32 → backend Python
    esp32_api_token: str

    # Servidor
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

---

## 6. Sin persistencia local

**Decisión arquitectónica:** el backend Python NO guarda nada. Ni BD, ni archivos, ni cache.

| Necesidad | Dónde vive |
|---|---|
| Historial de auditorías | MySQL del POS Laravel (tabla `auditorias_visuales`) |
| Imágenes capturadas | `storage/app/auditorias/Y/m/d/` del POS Laravel |
| Thumbnails | El POS los genera con Intervention Image |
| Discrepancias | Tabla `discrepancias_inventario` del POS |
| Catálogo de productos | Tabla `productos` del POS |
| Ventas (para clasificar evento) | Tabla `detalle_ventas` del POS |
| Logs del análisis con Claude | stdout (Railway captura), structlog con correlation IDs |

Si el POS está caído, el backend Python devuelve **502** al ESP32 y el firmware reintenta. **No buffereamos** ni guardamos en cola local. KISS.

---

## 7. Manejo de errores

`interfaces/api/exception_handlers.py`
```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from domain.exceptions import (
    DomainError, CapturaInvalida, ConfianzaInsuficiente,
    POSNoDisponible, AnalizadorNoDisponible,
)

def registrar_handlers(app: FastAPI) -> None:
    @app.exception_handler(CapturaInvalida)
    async def _(req, exc):
        return JSONResponse(status_code=422, content={"error": "captura_invalida", "detail": str(exc)})

    @app.exception_handler(ConfianzaInsuficiente)
    async def _(req, exc):
        return JSONResponse(status_code=200, content={"warning": "baja_confianza", "detail": str(exc)})

    @app.exception_handler(POSNoDisponible)
    async def _(req, exc):
        return JSONResponse(status_code=502, content={"error": "pos_no_disponible", "detail": str(exc)})

    @app.exception_handler(AnalizadorNoDisponible)
    async def _(req, exc):
        return JSONResponse(status_code=502, content={"error": "ia_no_disponible", "detail": str(exc)})

    @app.exception_handler(DomainError)
    async def _(req, exc):
        return JSONResponse(status_code=400, content={"error": exc.__class__.__name__, "detail": str(exc)})
```

Las excepciones de infraestructura (httpx, anthropic) se traducen a excepciones de dominio dentro de los adaptadores (no leak).

---

## 8. Endpoints

Versionados desde el día 1: prefijo `/api/v1`.

### `POST /api/v1/auditoria/captura`
Recibe imagen multipart del ESP32. Headers requeridos:
- `Authorization: Bearer <ESP32_API_TOKEN>`
- `X-Nodo-Id`: MAC del ESP32 (ej. `14:c1:9f:c1:b7:60`)
- `X-Timestamp`: ISO 8601 con timezone (ej. `2026-05-23T14:32:11-05:00`)
- `X-Tipo-Evento`: opcional, default `rutina` (`auditoria_apertura|rutina|reposicion|discrepancia`)

Respuesta `201`:
```json
{
  "auditoria_id_pos": 1234,
  "accion_tomada": "validada_venta",
  "cantidad_total": 7,
  "confianza_general": 0.93,
  "espacios_vacios": true
}
```

### `GET /api/v1/health`
Sin auth. `{"status": "ok", "timestamp": "..."}`. Para que el ESP32 verifique conectividad al arrancar.

**NO existe** `/api/v1/auditorias` — el listado/dashboard vive en el POS Laravel (`/auditorias` web).

---

## 9. Middleware y observabilidad

`interfaces/api/middleware.py` agrega:
- **Correlation ID:** lee `X-Request-Id` o genera uno; lo propaga al contexto de structlog y al header de salida al POS.
- **Logging de cada request:** método, path, status, duración, correlation_id, nodo_id.
- **CORS:** habilitado desde el boot (`CORSMiddleware`).
- **Rate limit interno** opcional con `asyncio.Semaphore` en el adaptador de Claude (no en el caso de uso).

---

## 10. Testing

### Unit (sin red, milisegundos)
- `tests/unit/application/test_procesar_captura.py` — usa un `FakeAnalizador` que devuelve un `AnalisisImagen` fijo y un `MockPOSClient`. Verifica que el caso de uso:
  - Llama al analizador con los bytes recibidos.
  - Pasa el payload correcto al POS (campos exactos del contrato).
  - Devuelve `ResultadoCaptura` con la respuesta del POS.

### Integration
- `tests/integration/test_api_captura.py` — FastAPI `TestClient` con DI sobrescrita (`app.dependency_overrides`) inyectando `MockPOSClient` y `FakeAnalizador`. Cubre auth, headers, payloads.

### E2E opcional (manual)
- Postman → backend Python local → POS Laravel local (`http://localhost/SistemaPosV2/public/api/vision/auditoria/registrar`) con token Sanctum real.

**Patrón clave** verificado en docs FastAPI vía Context7: sobrescribir dependencias en tests es trivial gracias a `Depends()`:
```python
app.dependency_overrides[get_pos_client] = lambda: MockPOSClient()
```

---

## 11. Variables de entorno (`.env.example`)
```env
# API de Claude
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-6

# POS Laravel (local en desarrollo, Railway en producción)
POS_URL=http://localhost/SistemaPosV2/public
POS_TOKEN=token_emitido_por_artisan_integracion_generar-token-python
USE_MOCK_POS=false

# Auth ESP32 → backend Python
ESP32_API_TOKEN=token_compartido_con_el_firmware

# Servidor
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
```

**Importante**: el `POS_TOKEN` se genera ejecutando en el repo del POS:
```bash
php artisan integracion:generar-token-python
```
Y se pega tal cual en el `.env` del backend Python.

---

## 12. `requirements.txt`
```
fastapi
uvicorn[standard]
anthropic
httpx
pydantic
pydantic-settings
python-dotenv
python-multipart
structlog
pytest
pytest-asyncio
```

**No hay** sqlalchemy, supabase, alembic, pillow, opencv. Eliminados.

---

## 13. Orden de implementación recomendado

Construir por **capas, de adentro hacia afuera**. Cada paso entrega valor testeable.

1. **Bootstrapping** — `pyproject.toml`, `requirements.txt`, `.env.example`, `shared/config.py`, `shared/logger.py`, `main.py` con `/api/v1/health`.
2. **Dominio puro** — entidades, value objects, excepciones. **Tests unitarios primero**. Sin tocar FastAPI ni HTTP.
3. **Puertos** — `IAnalizadorImagen`, `IPOSClient` como Protocols.
4. **Caso de uso `ProcesarCaptura`** — con fakes de los dos puertos en tests.
5. **Adaptador POS mock** (`MockPOSClient`) — destraba desarrollo offline.
6. **Adaptador POS real** (`LaravelPOSClient`) — con httpx async + token Sanctum.
7. **Adaptador Claude** (`ClaudeAnalizador`) — con prompt + parser JSON robusto.
8. **Router HTTP `/auditoria/captura`** + wiring DI completo + auth Bearer.
9. **Middleware + exception handlers + CORS + correlation ID + structlog.**
10. **Tests de integración** con FastAPI TestClient.
11. **Dockerfile** + deploy a Railway.

**Importante**: antes del paso 6, generar el token Sanctum del POS:
```bash
cd C:\xampp\htdocs\SistemaPosV2
php artisan integracion:generar-token-python
```

---

## 14. Estrategia de prueba (fases)

| Fase | Qué se prueba | Cómo |
|---|---|---|
| 1 | Dominio y caso de uso | `pytest tests/unit/` — sin red |
| 2 | API HTTP del backend | `pytest tests/integration/` con `MockPOSClient` y `FakeAnalizador` |
| 3 | Claude real con imagen de estante | Postman → `/api/v1/auditoria/captura` con `USE_MOCK_POS=true` |
| 4 | POS Laravel local | XAMPP + token real, `USE_MOCK_POS=false`, `POS_URL=http://localhost/SistemaPosV2/public` |
| 5 | ESP32 real en la misma WiFi | Hotspot del celular, ESP32 → backend local |
| 6 | Producción | Backend en Railway, POS en Railway, ESP32 con URL pública del backend |

---

## 15. Buenas prácticas adicionales

1. **Idempotencia (cuando esté en el POS)**: el POS debe agregar columna `request_id UNIQUE` a `auditorias_visuales`. El backend Python ya envía `X-Request-Id` en cada llamada (lo propaga el middleware).
2. **Backpressure de Claude**: `asyncio.Semaphore(N)` dentro de `ClaudeAnalizador` para limitar llamadas concurrentes (rate limits de Anthropic).
3. **Logging estructurado**: structlog con campos `correlation_id`, `nodo_id`, `accion_tomada`, `pos_status`. Facilita debugging cuando el POS rechaza.
4. **No leak de excepciones de infraestructura**: `httpx.HTTPError` y `anthropic.APIError` se atrapan dentro del adaptador y se relanzan como excepciones de dominio (`POSNoDisponible`, `AnalizadorNoDisponible`).
5. **DI sin singletons globales**: todo se inyecta vía `Depends()`. Los providers usan `@lru_cache` solo donde tiene sentido (Settings, AsyncAnthropic client).
6. **CORS** habilitado desde el principio.
7. **Versionado de API** (`/api/v1`) desde el día 1 — el firmware del ESP32 se rompe si cambia el contrato.
8. **No commitear `.env`** — solo `.env.example`.

---

## 16. Mapeo: spec anterior → spec actual

| Spec anterior | Spec actual |
|---|---|
| `app/services/claude_service.py` | `infrastructure/ia/claude_analizador.py` (implementa `IAnalizadorImagen`) |
| `app/services/pos_service.py` (5 métodos) | `infrastructure/pos/laravel_pos_client.py` (1 método: `notificar_auditoria`) |
| `app/services/imagen_service.py` | **ELIMINADO** (POS guarda la imagen) |
| `app/services/validacion_service.py` | **ELIMINADO** (POS clasifica en `AuditoriaVisualService::validarContraVentas`) |
| `app/models/schemas.py` (god file) | Dividido: `domain/entities/`, `domain/value_objects/`, `application/dtos/`, `interfaces/api/v1/schemas/` |
| (no existía) | `application/ports/` — interfaces |
| (Supabase) | **ELIMINADO** — sin persistencia local |
| (ClasificadorEvento) | **ELIMINADO** — POS clasifica |
| (Anotador OpenCV) | **ELIMINADO** — over-engineered |

---

## 17. Contrato con el POS Laravel (referencia rápida)

Request:
```
POST {POS_URL}/api/vision/auditoria/registrar
Authorization: Bearer {POS_TOKEN}
Content-Type: application/json

{
  "nodo_id": "14:c1:9f:c1:b7:60",
  "imagen_base64": "...",
  "timestamp_captura": "2026-05-23T14:32:11-05:00",
  "tipo_evento": "rutina",
  "respuesta_ia": {
    "cantidad_total": 7,
    "espacios_vacios": true,
    "confianza_general": 0.93,
    "productos_detectados": [
      {"nombre": "Coca-Cola 1.5L", "cantidad": 4, "confianza": 0.95},
      {"nombre": "Inca Kola 1.5L", "cantidad": 3, "confianza": 0.92}
    ]
  }
}
```

Response `201`:
```json
{
  "success": true,
  "auditoria_id": 1234,
  "accion_tomada": "validada_venta"
}
```

Valores posibles de `accion_tomada`:
- `pendiente` — primera captura del nodo o producto no matcheó, sin clasificar todavía.
- `validada_venta` — bajó stock y hay ventas que lo justifican.
- `merma_sospechosa` — bajó stock sin ventas. El POS ya disparó WhatsApp al dueño.
- `reposicion_confirmada` — subió stock.

---

## 18. Notas sobre el modelo de Claude

- `claude-sonnet-4-6` es multimodal y acepta imágenes en base64.
- Tamaño SVGA 800x600 JPEG es óptimo: balance entre detalle y tokens.
- El adaptador `ClaudeAnalizador` debe encapsular reintentos exponenciales ante 429/5xx (usar `tenacity` o lógica propia).
- El prompt vive en `infrastructure/ia/prompts.py` — fácil de iterar sin tocar la lógica.

---

## 19. Deployment a Railway

El backend Python se despliega a Railway cuando lo necesiten en producción/demo final. **El código no cambia** entre local y Railway: solo cambian las variables de entorno.

### Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ src/
ENV PORT=8000
CMD uvicorn src.main:app --host 0.0.0.0 --port $PORT
```

Sin dependencias del sistema (no usamos OpenCV ni Pillow).

### Variables en Railway
```
ANTHROPIC_API_KEY
CLAUDE_MODEL=claude-sonnet-4-6
POS_URL=https://tu-pos.up.railway.app           # URL pública del POS en Railway
POS_TOKEN                                        # token Sanctum del usuario integracion-api
USE_MOCK_POS=false
ESP32_API_TOKEN
```

`BACKEND_PORT` lo gestiona Railway vía `$PORT`.

### Checklist migración local → Railway
- [ ] `Dockerfile` probado localmente con `docker build && docker run`.
- [ ] `requirements.txt` con versiones pineadas (ej. `fastapi==0.118.0`).
- [ ] Variables sensibles configuradas en Railway, NO en el repo.
- [ ] Endpoint `/api/v1/health` responde 200 tras el deploy.
- [ ] Actualizar firmware del ESP32 con la URL pública de Railway.

### Lo que NO necesita migrar
- **POS Laravel**: ya está (o estará) en Railway. URL no cambia.
- **API de Claude**: cloud por definición.
- **BD del POS**: vive con el POS en Railway.

El único elemento que se mueve es el código Python. Todo lo demás es estable.

---

Fin del plan. Este documento es el **contrato arquitectónico** del backend. Si Claude Code propone código que viola las reglas de la sección 2, rechazarlo.
