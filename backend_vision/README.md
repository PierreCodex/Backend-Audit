# Backend Visión — Auditoría Visual de Inventario

Backend Python (FastAPI) que recibe imágenes capturadas por un ESP32-S3-CAM, las analiza con Claude Sonnet 4.6 y reenvía el resultado al POS Laravel (`SistemaPosV2`) para que clasifique el evento (venta/merma/reposición) y dispare alertas por WhatsApp.

Arquitectura: **Clean Architecture** estricta (4 capas) + **stateless** (sin BD propia).

```
ESP32-S3-CAM  →  Backend Python  →  POS Laravel  →  WhatsApp (Twilio)
                  (este proyecto)     (clasifica)
                       │
                       ↓
                  Claude Sonnet 4.6
```

Plan arquitectónico completo: ver `../BACKEND_PYTHON_SPEC_CLEAN.md`.

---

## Estructura

```
src/
├── domain/          # Capa 1 — entidades, value objects, excepciones (sin deps externas)
├── application/     # Capa 2 — puertos (Protocols) + caso de uso ProcesarCaptura
├── infrastructure/  # Capa 3 — adaptadores Claude + Laravel POS
├── interfaces/      # Capa 4 — FastAPI routers, schemas, middleware, security
├── shared/          # config + logger
└── main.py
tests/
├── unit/            # dominio + caso de uso con fakes
└── integration/     # FastAPI TestClient
```

---

## Setup local (Windows / PowerShell)

```powershell
cd F:\PERSONAL_JEAN\project-arduino\backend_vision

# 1. Crear entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Crear .env desde el template
Copy-Item .env.example .env
# Editar .env y completar ANTHROPIC_API_KEY, POS_TOKEN, ESP32_API_TOKEN
```

### Generar el token del POS

En otra terminal, dentro del repo del POS:
```powershell
cd C:\xampp\htdocs\SistemaPosV2
php artisan integracion:generar-token-python
```

Copiar el token que imprime → pegarlo en `.env` como `POS_TOKEN`.

---

## Correr el backend

```powershell
# Asegurar que XAMPP/Apache esté corriendo (para el POS Laravel local)
# Luego:
$env:PYTHONPATH = "$PWD\src"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Probar:
- Health: http://localhost:8000/api/v1/health
- Docs Swagger: http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json

---

## Correr en modo mock (sin POS real)

Útil para desarrollo temprano:
```powershell
# en .env:
USE_MOCK_POS=true
```

El backend usa `MockPOSClient` que simula respuestas. Permite probar el flujo Claude → respuesta sin tener Laravel corriendo.

---

## Tests

```powershell
$env:PYTHONPATH = "$PWD\src"

# Todos los tests
pytest

# Solo unit (rápido, sin red)
pytest tests/unit

# Solo integración (FastAPI TestClient)
pytest tests/integration

# Verbose con output
pytest -v -s
```

---

## Probar con Postman / curl

### Health
```bash
curl http://localhost:8000/api/v1/health
```

### Captura
```bash
curl -X POST http://localhost:8000/api/v1/auditoria/captura ^
  -H "Authorization: Bearer esp32-test-token" ^
  -H "X-Nodo-Id: 14:c1:9f:c1:b7:60" ^
  -H "X-Timestamp: 2026-05-23T14:32:11-05:00" ^
  -H "X-Tipo-Evento: rutina" ^
  -H "X-Request-Id: req-001" ^
  -F "imagen=@estante.jpg"
```

Response esperada (201):
```json
{
  "auditoria_id_pos": 1234,
  "accion_tomada": "validada_venta",
  "cantidad_total": 7,
  "confianza_general": 0.93,
  "espacios_vacios": true,
  "idempotent_replay": false
}
```

---

## Variables de entorno

| Variable | Descripción |
|---|---|
| `ANTHROPIC_API_KEY` | API key de Anthropic (https://console.anthropic.com) |
| `CLAUDE_MODEL` | Modelo a usar (default: `claude-sonnet-4-6`) |
| `POS_URL` | Base URL del POS Laravel (`http://localhost/SistemaPosV2/public` local; URL de Railway en producción) |
| `POS_TOKEN` | Token Sanctum del usuario `integracion-api` (lo genera el comando artisan del POS) |
| `USE_MOCK_POS` | `true` en desarrollo offline; `false` para apuntar al POS real |
| `ESP32_API_TOKEN` | Token Bearer compartido con el firmware del ESP32 |
| `BACKEND_HOST` | Default `0.0.0.0` |
| `BACKEND_PORT` | Default `8000` |
| `CONFIANZA_MINIMA` | Umbral mínimo (0–1) — futuro, para descartar capturas de baja confianza |

---

## Endpoints

### `GET /api/v1/health`
Health check sin auth. Devuelve `{status, timestamp, version}`.

### `POST /api/v1/auditoria/captura`
Recibe imagen multipart del ESP32 y la procesa.

**Headers requeridos:**
- `Authorization: Bearer <ESP32_API_TOKEN>`
- `X-Nodo-Id`: MAC del ESP32 (ej. `14:c1:9f:c1:b7:60`)
- `X-Timestamp`: ISO 8601 con timezone
- `X-Tipo-Evento`: opcional (`auditoria_apertura|rutina|reposicion|discrepancia`)
- `X-Request-Id`: UUID opcional para idempotencia

**Body:** `multipart/form-data` con campo `imagen` (JPEG).

---

## Deploy a Railway

1. **Crear proyecto** en Railway apuntando a este repo.
2. Railway detecta el `Dockerfile` y construye automáticamente.
3. **Variables de entorno**: configurar las mismas del `.env` local pero apuntando a las URLs públicas:
   - `POS_URL=https://tu-pos.up.railway.app`
   - Todas las demás iguales.
4. **Health check**: configurar `/api/v1/health` como ruta de health check.
5. Actualizar el firmware del ESP32 con la URL pública del backend.

El POS y el backend Python deberían estar en el **mismo proyecto de Railway** para latencia interna mínima.

---

## Convenciones

- **Idioma**: identificadores, comentarios y logs en español (igual que el POS Laravel).
- **Async**: todo el código IO-bound es `async def`. No bloquear el event loop.
- **Sin estado**: nada se persiste en Python. Cualquier dato que sobreviva al request vive en el POS.
- **Clean Architecture**: las reglas de dependencia están documentadas en `../BACKEND_PYTHON_SPEC_CLEAN.md` (sección 2). Romperlas requiere justificación.

---

## Troubleshooting

| Síntoma | Causa probable |
|---|---|
| `401 Token inválido` | El header `Authorization: Bearer ...` no coincide con `ESP32_API_TOKEN` en `.env` |
| `502 pos_no_disponible` | XAMPP no está corriendo, `POS_URL` mal configurada, o `POS_TOKEN` expirado |
| `502 ia_no_disponible` | `ANTHROPIC_API_KEY` mal o sin créditos en Anthropic |
| `422 valor_invalido NodoId` | El `X-Nodo-Id` que envió el ESP32 es muy corto o vacío |
| `400 La imagen está vacía` | El multipart llegó sin bytes |
| Tests fallan con `ModuleNotFoundError` | Falta `$env:PYTHONPATH = "$PWD\src"` antes de correr `pytest` |

---

## Próximos pasos pendientes (no parte del MVP)

- Aplicar ajustes pendientes al POS según `../POS_AJUSTES_PENDIENTES.md` (idempotencia, `timestamp_captura` required, normalización de matching).
- Programar firmware del ESP32 para que envíe a este backend.
- Pruebas end-to-end con ESP32 real en la WiFi del hotspot.
- Deploy a Railway (cuando esté listo el flujo local completo).