# Progreso del proyecto — 



**Última actualización:** 2026-05-29 (✅ **pipeline ESP32→backend→Claude→POS funcionando end-to-end**; causa raíz era el Firewall de Windows; firmware bajado a XGA; stream con doble servidor. Ver `REPORTE_SESION_2026-05-29.md`)

Tracker de tareas del proyecto IoT (ESP32-S3-CAM + Backend Python + POS Laravel). Se actualiza después de cada paso. Lo hecho lleva ✅, lo en curso 🔄, lo pendiente 🔲.

---

## Estado general

```
┌──────────────────┐    ┌────────────────────┐    ┌──────────────────┐
│  ESP32-S3-CAM    │ → │  Backend Python     │ → │  POS Laravel     │
│  ✅ Flasheado    │    │  ✅ Implementado    │    │  ✅ Implementado │
│  ✅ Captura→POST │    │  ✅ Claude validado │    │  🔄 Ajustes      │
│  ⚠️ Stream WiFi  │    │  ✅ Recibe del ESP32│    │  (mock por ahora)│
└──────────────────┘    └────────────────────┘    └──────────────────┘
                              │                          │
                              ↓                          ↓
                        Claude Sonnet 4.6            WhatsApp (Twilio)
                        ✅ Probado con Postman       ✅ Configurado
```

### Avance global

| Componente | Avance |
|---|---|
| POS Laravel — código | ~95% (faltan ajustes finos del `POS_AJUSTES_PENDIENTES.md`) |
| Backend Python — código | 100% |
| Backend Python — setup local probado | 100% (health responde 200, 27/27 tests OK) |
| Backend Python — integrado con Claude real | ✅ 100% (validado con Postman + PNG real, Claude detectó 15 productos, confianza 91%) |
| Firmware ESP32 — código | 100% (fuente real en `sketch_may24a/`, no en el MD viejo) |
| Firmware ESP32 — flasheado en placa | ✅ 100% (corriendo, captura XGA llega al backend) |
| Integración ESP32 → backend → Claude → POS | ✅ funcionando (HTTP 201; falta POS real, hoy mock) |
| Stream en vivo para enfocar | ⚠️ inestable (enlace WiFi, no firmware) — enfocar por opción B |
| Deploy Railway | 0% |

---

## 1. POS Laravel (`C:\xampp\htdocs\SistemaPosV2`)

### Implementado
- [x] Migraciones: `auditorias_visuales`, `discrepancias_inventario`, `nodos_iot`
- [x] Modelos Eloquent con relaciones, scopes y soft deletes
- [x] 6 endpoints API `/api/vision/*` con Sanctum + abilities
- [x] Controllers en `app/Http/Controllers/Api/Vision/`
- [x] Services en `app/Services/Vision/` (AuditoriaVisualService, DiscrepanciaService, NotificacionWhatsappService)
- [x] FormRequests con validación estricta
- [x] Comando artisan `integracion:generar-token-python`
- [x] Seeder `UsuarioIntegracionPythonSeeder`
- [x] Config Twilio + auditoría en `config/services.php`
- [x] Vistas web para auditorías, discrepancias, nodos IoT
- [x] Lógica de clasificación: venta_validada / merma_sospechosa / reposición

### Pendiente (ver `POS_AJUSTES_PENDIENTES.md`)
- [ ] 🔴 #1 — Agregar idempotencia con `request_id UNIQUE` (migración + service + FormRequest)
- [ ] 🟡 #2 — `timestamp_captura` requerido + columna `capturado_at`
- [ ] 🟡 #3 — Normalización del matching de productos (Coca-Cola ↔ Coca Cola)
- [ ] 🟢 #4 — Borrar carpetas flat basura + archivos sueltos en la raíz
- [ ] 🟢 #5 — Documentar `/discrepancia` como endpoint debug
- [ ] 🟢 #6 — (Opcional) Aceptar multipart/form-data además de base64
- [ ] Tests del POS (`tests/Feature/Api/AuditoriaVisualIdempotenciaTest.php`, etc.)

---

## 2. Backend Python (`F:\PERSONAL_JEAN\project-arduino\backend_vision`)

### Implementado (Clean Architecture, 4 capas)
- [x] **Bootstrapping**: pyproject.toml, requirements.txt, .env.example, .gitignore, Dockerfile, .dockerignore
- [x] **shared/**: config (pydantic-settings) + logger (structlog JSON)
- [x] **domain/**: entidades (Deteccion, AnalisisImagen), value objects (NodoId, Confianza, TimestampCaptura), excepciones
- [x] **application/ports/**: IAnalizadorImagen, IPOSClient (Protocols)
- [x] **application/dtos/**: CapturaCommand, RespuestaPOS, ResultadoCaptura
- [x] **application/use_cases/**: ProcesarCaptura (orquesta los 3 pasos)
- [x] **infrastructure/ia/**: ClaudeAnalizador (con reintentos tenacity) + prompts
- [x] **infrastructure/pos/**: LaravelPOSClient (httpx async) + MockPOSClient (con simulación idempotencia)
- [x] **interfaces/api/**: dependencies (DI wiring), security (Bearer ESP32), middleware (CORS + correlation ID + logging), exception_handlers
- [x] **interfaces/api/v1/routers/**: auditoria.py (POST /captura), health.py
- [x] **interfaces/api/v1/schemas/**: CapturaResponse, HealthResponse, ErrorResponse
- [x] **main.py**: lifespan + wiring completo
- [x] **tests/unit/**: domain (value objects + analisis_imagen), application (procesar_captura con FakeAnalizador)
- [x] **tests/integration/**: API HTTP con FastAPI TestClient + DI override
- [x] **README.md** con instrucciones completas

### Setup local (paso 1 de la hoja de ruta)
- [x] venv creado con Python 3.13.3
- [x] 33 dependencias instaladas
- [x] `.env` creado con `USE_MOCK_POS=true`
- [x] `uvicorn` arrancó en `http://127.0.0.1:8000`
- [x] `GET /api/v1/health` → 200 OK con JSON estructurado
- [x] structlog emite logs con correlation_id
- [x] **27/27 tests pasan** (1 bug detectado y arreglado en security.py)

### Pendiente
- [x] **Paso 2**: completar valores reales en `.env`:
  - [x] `ANTHROPIC_API_KEY` con key real ✅
  - [ ] `ESP32_API_TOKEN` con token aleatorio seguro (actualmente `cambiar_por_token_seguro`, sirve para pruebas)
- [x] **Paso 2**: probar `POST /api/v1/auditoria/captura` con `USE_MOCK_POS=true` + imagen real de estante → ✅ Claude detectó 15 productos con 91% confianza
- [ ] **Paso 3**: ejecutar `php artisan integracion:generar-token-python` en el POS, pegar token en `.env` como `POS_TOKEN`
- [ ] **Paso 4**: cambiar `USE_MOCK_POS=false`, probar end-to-end Python ↔ POS Laravel local
- [ ] **Paso 5**: probar con ESP32 real en la WiFi del hotspot (cuando exista firmware)
- [ ] **Paso 6**: deploy a Railway

### Mejoras detectadas durante las pruebas
- [x] Bug fix `security.py`: `Authorization` header opcional → devuelve 401 (no 422) cuando falta
- [x] Mejora `claude_analizador.py`: detección dinámica de `media_type` (JPEG/PNG/GIF/WebP) por magic bytes — antes hardcodeaba a JPEG y fallaba con PNG

---

## 3. Firmware ESP32-S3-CAM

### Hardware
- [x] Nodo identificado: ESP32-S3 N16R8 CAM con OV3660
- [x] MAC: `14:c1:9f:c1:b7:60`
- [x] Configuración documentada (`HARDWARE_ESP32_CONFIG.md`)

### Código generado (ver `firmware_esp32/`)
- [x] **`FIRMWARE_ESP32_CODIGO.md`** — código completo de los 3 archivos:
  - `firmware_esp32.ino` — sketch principal
  - `secrets.h` — WiFi + tokens (placeholders)
  - `config.h` — constantes ajustables
- [x] **`FIRMWARE_ESP32_SETUP.md`** — guía paso a paso para Arduino IDE
- [x] Conexión WiFi con reconexión automática
- [x] Sincronización NTP (Lima UTC-5) → timestamp ISO 8601
- [x] Captura UXGA 1600x1200 JPEG calidad 10 (perfil ESP32S3_EYE) — actualizado desde SVGA tras detectar borrosidad
- [x] Sensor settings completos (sharpness=2, denoise, AEC/AGC/AWB, lens correction)
- [x] Warm-up de 3 frames antes de cada captura (AEC/AWB converge tras 5 min de inactividad)
- [x] HTTP POST multipart al backend (en PSRAM para no agotar heap)
- [x] Headers Authorization Bearer + X-Nodo-Id + X-Timestamp + X-Request-Id + X-Tipo-Evento
- [x] UUID-like Request ID (MAC + millis + random) para idempotencia
- [x] Reintentos con backoff exponencial (2s → 4s → 8s)
- [x] LED RGB WS2812 en GPIO 48 — azul/verde/amarillo/rojo
- [x] Captura inmediata al arrancar + cada 5 min
- [x] Auto-reinicio si la cámara o WiFi fallan en setup

### Estado real del firmware (sesión 2026-05-29)

**Fuente de verdad: carpeta `sketch_may24a/` (4 archivos), NO el MD viejo.**
Hay dos copias idénticas: `C:\Users\pierr\Desktop\arduino\sketch_may24a\` (Arduino IDE)
y `F:\PERSONAL_JEAN\project-arduino\sketch_may24a\` (versionada). FQBN para compilar:
`esp32:esp32:esp32s3:PSRAM=opi,FlashSize=16M,CDCOnBoot=default,PartitionScheme=huge_app`.

- [x] Flasheado y corriendo en la placa (COM3, chip CH343)
- [x] **Causa raíz "nada llega al backend": Firewall de Windows** bloqueaba TCP 8000 → resuelto con `netsh`
- [x] Resolución bajada **UXGA → XGA** (UXGA daba `send payload failed` + `cam_hal: FB-OVF`)
- [x] `BACKEND_HOST` corregido a `192.168.1.9` en `secrets.h`
- [x] Captura llega al backend → Claude responde → POS devuelve `auditoria_id_pos` (HTTP 201)
- [x] Stream: doble servidor (`:80` página, `:81` stream) + `WiFi.setSleep(false)` + `fb_count=3`
- [x] `USB CDC On Boot = Disabled` (para ver Serial por COM3)
- [ ] ⚠️ Stream en vivo NO entrega imagen confiable — enlace WiFi lossy (sospecha: adaptador USB TP-Link / USB 3.0). Físico, no firmware.

### Milestone: Nitidez de capturas — enfoque por opción B (sin stream)

El OV3660 no tiene autofocus (foco manual con el aro). El stream para enfocar quedó
inestable, así que **se enfoca con capturas directas** (confiable):

- [ ] **Acción del user**: apuntar al estante CON LUZ → apretar RST → revisar foto en `storage/debug/` → girar aro → repetir
- [ ] Validar captura nítida y con luz (de noche sale negra → Claude cuenta 0)
- [ ] Confirmar conteo de Claude con imagen buena (esperado ≥17/18 = ≥94%)
- [ ] (Opcional) Subir resolución XGA → SXGA → UXGA validando, una vez estable y con luz

---

## 4. Integración end-to-end (ESP32 → Python → POS → WhatsApp)

- [x] **ESP32 alcanza al backend en la WiFi de casa** (tras abrir el Firewall) → captura llega
- [x] **Captura: ESP32 → backend Python → Claude → POS (mock)** → HTTP 201 con `auditoria_id_pos`
- [ ] Backend Python + POS Laravel **real** hablando local (hoy `USE_MOCK_POS=true`)
- [ ] Cadena completa hasta WhatsApp llega al dueño (falta POS real + Twilio)
- [ ] Prueba de merma: comparar dos capturas con cambio → verificar que llega alerta WhatsApp
- [ ] Prueba de idempotencia: cortar internet a mitad de envío → ESP32 reintenta → solo 1 registro en BD del POS

---

## 5. Deploy a producción / demo

- [ ] POS Laravel desplegado en Railway
- [ ] Backend Python desplegado en Railway (Dockerfile listo)
- [ ] Firmware ESP32 actualizado con URL pública del backend
- [ ] Twilio configurado con número real del dueño
- [ ] Pruebas de demo final con WiFi de hotspot estable
- [ ] Documentación de uso para el dueño/jurado

---

## Documentos del proyecto

| Archivo | Propósito |
|---|---|
| `BACKEND_PYTHON_SPEC_CLEAN.md` | Contrato arquitectónico del backend Python (Clean Architecture, stateless) — **REFERENCIA PRINCIPAL** |
| `BACKEND_PYTHON_SPEC.md` | Spec original (obsoleto, no seguir) |
| `POS_AJUSTES_PENDIENTES.md` | Mini-plan de cambios pendientes para el POS Laravel |
| `HARDWARE_ESP32_CONFIG.md` | Configuración del nodo ESP32-S3-CAM |
| `PROGRESO.md` | **Este archivo** — tracker general del proyecto |
| `REPORTE_SESION_2026-05-29.md` | **Reporte de la sesión de depuración** — causas raíz, comandos, archivos Arduino, próximos pasos |
| `sketch_may24a/` (carpeta) | **FUENTE DE VERDAD del firmware** (4 archivos: .ino, config.h, secrets.h, camera_pins.h) |
| `backend_vision/README.md` | Setup y operación del backend Python |
| `firmware_esp32/FIRMWARE_ESP32_CODIGO.md` | ⚠️ DESACTUALIZADO (UXGA, 1 server). Usar `sketch_may24a/` en su lugar |
| `firmware_esp32/FIRMWARE_ESP32_SETUP.md` | Setup paso a paso del Arduino IDE para flashear el firmware |
| `firmware_esp32/FIRMWARE_ENFOQUE.md` | Sketch temporal para ajustar el foco del OV3660 con stream MJPEG en navegador |
| `C:\xampp\htdocs\SistemaPosV2\plan_implementacion_vision.md` | Plan original del módulo de visión en el POS |

---

## Cómo retomar después de cerrar el editor

```powershell
# 1. Abrir VSCode en F:\PERSONAL_JEAN\project-arduino
# 2. Leer este PROGRESO.md (en el editor o desde la terminal):
cat F:\PERSONAL_JEAN\project-arduino\PROGRESO.md

# 3. Buscar el primer 🔲 sin marcar — ese es el siguiente paso.
# 4. Si es algo del backend Python:
cd F:\PERSONAL_JEAN\project-arduino\backend_vision
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --app-dir src
# (--host 0.0.0.0 OBLIGATORIO para que el ESP32 llegue; --app-dir src porque app vive en src/main.py)
```

> 🔌 Para reabrir/retomar el hardware: leer `REPORTE_SESION_2026-05-29.md`.
> Firmware real en `sketch_may24a/`. Si el ESP32 da rojo y el backend está OK, revisar
> la regla de firewall (TCP 8000) y que la IP de la PC siga siendo la de `secrets.h`.