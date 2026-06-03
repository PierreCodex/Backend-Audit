# Setup del firmware ESP32-S3-CAM — paso a paso

Guía para llevar el código de `FIRMWARE_ESP32_CODIGO.md` al Arduino IDE y dejarlo enviando capturas al backend Python.

**Pre-requisito ya validado** (ver `HARDWARE_ESP32_CONFIG.md`):
- Arduino IDE 2.3.8 instalado
- Paquete `esp32 by Espressif Systems` versión 3.3.8
- La cámara ya funcionó con el ejemplo `CameraWebServer`

---

## Paso 1 — Instalar la librería Adafruit NeoPixel (LED RGB)

Esta es la única dependencia nueva que necesitás.

1. En Arduino IDE: **Tools → Manage Libraries...** (o `Ctrl+Shift+I`)
2. Buscar: `Adafruit NeoPixel`
3. Instalar la última versión (≥ 1.12.x)

Las demás librerías (`WiFi.h`, `esp_camera.h`, `HTTPClient.h`, `time.h`) ya vienen con el paquete `esp32` de Espressif.

---

## Paso 2 — Crear el sketch

### 2.1 Crear la carpeta del sketch

En tu carpeta de sketches de Arduino (por defecto `Documents\Arduino\` en Windows), creá una carpeta llamada **exactamente** `firmware_esp32`.

### 2.2 Crear los 3 archivos

Dentro de `firmware_esp32\`, creá los siguientes archivos vacíos:

```
firmware_esp32\
├── firmware_esp32.ino   ← sketch principal
├── secrets.h            ← credenciales (NO commitear)
└── config.h             ← constantes
```

> **Cómo crear `.h` desde el IDE**: en el sketch abierto, hacé clic en la flecha ▼ arriba a la derecha → **New Tab** → escribí el nombre con extensión (ej. `secrets.h`).

### 2.3 Pegar el código

Abrí `FIRMWARE_ESP32_CODIGO.md` y copiá cada bloque a su archivo correspondiente:

| Bloque en el `.md` | Pegar en |
|---|---|
| Bloque 1 (`secrets.h`) | `secrets.h` |
| Bloque 2 (`config.h`) | `config.h` |
| Bloque 3 (`firmware_esp32.ino`) | `firmware_esp32.ino` |

---

## Paso 3 — Configurar `secrets.h` con TUS valores

Editá `secrets.h`. Tres cosas para completar.

### 3.1 `WIFI_SSID` y `WIFI_PASSWORD`

Las del hotspot del celular que vas a usar en la demo.

> Tip: poné el celular a generar el hotspot AHORA mismo y conectá tu Mac/PC también. Así el ESP32 y el backend están en la misma red desde el inicio.

### 3.2 `BACKEND_HOST` — IP local de tu Mac/PC

**Estando conectado al hotspot del celular**, abrí una terminal y averiguá tu IP local:

**Windows (PowerShell o CMD):**
```
ipconfig
```
Buscá la sección **"Adaptador de LAN inalámbrica Wi-Fi"** → línea **"Dirección IPv4"**.
Suele ser algo como `192.168.43.123` o `172.20.10.5`.

**macOS:**
```
ipconfig getifaddr en0
```

**Linux:**
```
hostname -I
```

Pegala en `BACKEND_HOST`. El puerto deja `8000`.

### 3.3 `BACKEND_TOKEN`

Tiene que coincidir EXACTO con el valor de `ESP32_API_TOKEN` en `backend_vision\.env`.

Si todavía no decidiste el token, generá uno aleatorio y poné el mismo en los dos lados. Ejemplo:

```
esp32_AB12_CD34_EF56_demo_2026
```

Editá `backend_vision\.env`:
```
ESP32_API_TOKEN=esp32_AB12_CD34_EF56_demo_2026
```

Y en `secrets.h`:
```cpp
#define BACKEND_TOKEN  "esp32_AB12_CD34_EF56_demo_2026"
```

---

## Paso 4 — Configurar el board en el IDE

**Tools** → seleccionar exactamente:

| Parámetro | Valor |
|---|---|
| Board | `ESP32S3 Dev Module` |
| USB CDC On Boot | `Enabled` |
| CPU Frequency | `240MHz (WiFi)` |
| Flash Mode | `QIO 80MHz` |
| Flash Size | `16MB (128Mb)` |
| Partition Scheme | `16M Flash (3MB APP/9.9MB FATFS)` |
| **PSRAM** | **`OPI PSRAM`** ⚠️ crítico |
| Upload Mode | `UART0 / Hardware CDC` |
| Upload Speed | `921600` |
| USB Mode | `Hardware CDC and JTAG` |

⚠️ Sin **PSRAM = OPI PSRAM**, la cámara no inicializa (ya validado en `HARDWARE_ESP32_CONFIG.md`).

Después: **Tools → Port** y elegí el COM correcto del ESP32.

---

## Paso 5 — Verificar y subir

### 5.1 Verificar (compilar sin subir)

`Ctrl+R` o **Sketch → Verify/Compile**.

Si compila sin errores → seguir. Si hay error, revisar:
- Falta la librería Adafruit NeoPixel → volver al Paso 1.
- `'camera_pins.h': No such file` → asegurar que el board seleccionado es `ESP32S3 Dev Module` Y que tenés el paquete esp32 de Espressif (no el de Arduino).

### 5.2 Subir al ESP32

`Ctrl+U` o **Sketch → Upload**.

> **Si se queda en "Connecting..."**: mantené presionado **BOOT**, presioná y soltá **RST**, soltá **BOOT**, reintentá Upload (es comportamiento conocido de esta placa).

---

## Paso 6 — Monitorear por Serial

`Tools → Serial Monitor` (o `Ctrl+Shift+M`).

Configurar a **115200 baudios**.

Salida esperada al arrancar:

```
=== Firmware Auditoría Visual — ESP32-S3-CAM ===
[CAM] OK
[WiFi] Conectando a SSID=MiHotspot
.....
[WiFi] Conectado. IP=192.168.43.50  RSSI=-58 dBm
[NTP] Sincronizando hora...
.
[NTP] Hora local: 2026-05-23 14:32:11

========== Nueva captura ==========
[HTTP] POST http://192.168.43.123:8000/api/v1/auditoria/captura  (82431 bytes JPEG)
[HTTP]   X-Request-Id: 14C19FC1-B7600000-12345-ABCD
[HTTP] Intento 1/3
[HTTP] Status=201  Body={"auditoria_id_pos":1,"accion_tomada":"validada_venta","cantidad_total":7,"confianza_general":0.93,"espacios_vacios":true,"idempotent_replay":false}
[OK] Captura enviada y aceptada por el backend
```

LED verde encendido → todo funcionó.

---

## Paso 7 — Antes de probar: levantar el backend Python

En tu Mac/PC, **estando conectado al mismo hotspot**:

```powershell
cd F:\PERSONAL_JEAN\project-arduino\backend_vision
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

⚠️ El `--host 0.0.0.0` es **crítico** — si arrancás con `127.0.0.1` (default), el ESP32 NO podrá alcanzarlo desde la WiFi.

Verificá que el firewall de Windows permita conexiones entrantes al puerto 8000:
- Cuando arranques uvicorn por primera vez, Windows va a preguntar. Permitir en redes privadas.

---

## Diagnóstico de problemas comunes

| LED | Significado | Qué revisar |
|---|---|---|
| 🔵 Azul fijo | Conectando WiFi/NTP | Esperar 30s. Si no pasa: SSID/password mal. |
| 🟡 Amarillo | Sin WiFi | Hotspot del celular activo? ¿Mismo SSID que `secrets.h`? |
| 🔴 Rojo | Error backend | Backend Python corriendo? IP correcta en `BACKEND_HOST`? Firewall? `ESP32_API_TOKEN` coincide? |
| 🟢 Verde | OK | Todo bien — esperá 5 min para la próxima captura |

### Errores típicos en el Serial

| Mensaje | Causa probable |
|---|---|
| `[CAM] Init falló con error 0x...` | PSRAM mal configurada o pines incorrectos. Revisar Tools > PSRAM = OPI PSRAM. |
| `[HTTP] Falló: connection refused` | Backend no está corriendo, o está en `127.0.0.1` y no en `0.0.0.0`. |
| `[HTTP] Status=401` | El `BACKEND_TOKEN` de `secrets.h` no coincide con `ESP32_API_TOKEN` del `.env` del backend. |
| `[HTTP] Status=422 valor_invalido` | El `NODO_ID` o `X-Timestamp` no cumple las invariantes del dominio Python. |
| `[HTTP] Status=502 ia_no_disponible` | `ANTHROPIC_API_KEY` falso/inválido en el `.env` del backend. Probar primero con `USE_MOCK_POS=true` para descartar el flujo POS. |
| `[HTTP] Status=502 pos_no_disponible` | `USE_MOCK_POS=false` pero el POS Laravel no está corriendo o `POS_TOKEN` está mal. Ponerlo en `true` para probar sin POS real. |
| `[NTP] FALLÓ` | Hotspot bloquea NTP. El firmware sigue funcionando pero envía timestamp 1970. |

---

## Probar SIN el ESP32 primero (curl simulando una captura)

Mientras tengas el firmware listo pero no quieras flashear todavía, podés simular una captura desde tu PC con `curl`:

```powershell
# Crear una imagen de prueba (cualquier .jpg sirve)
$ts = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
curl.exe -X POST http://localhost:8000/api/v1/auditoria/captura `
  -H "Authorization: Bearer esp32_AB12_CD34_EF56_demo_2026" `
  -H "X-Nodo-Id: 14:c1:9f:c1:b7:60" `
  -H "X-Timestamp: $ts" `
  -H "X-Tipo-Evento: rutina" `
  -H "X-Request-Id: prueba-001" `
  -F "imagen=@C:\ruta\a\estante.jpg"
```

Si esto devuelve 201 → tu backend Python está bien y el problema (si lo hay) está en el firmware.

---

## Checklist final antes de la primera prueba real

- [ ] Adafruit NeoPixel instalada
- [ ] `secrets.h` con SSID, password y BACKEND_HOST correctos
- [ ] `BACKEND_TOKEN` idéntico en `secrets.h` y en `.env` del backend
- [ ] Board configurado con PSRAM = OPI PSRAM
- [ ] Sketch compila sin errores
- [ ] Sketch flasheado al ESP32
- [ ] Backend Python corriendo con `--host 0.0.0.0`
- [ ] Mac/PC y ESP32 conectados al mismo hotspot
- [ ] Firewall de Windows permite puerto 8000
- [ ] `USE_MOCK_POS=true` en `.env` (para esta primera prueba, sin necesidad de POS real)
- [ ] Serial Monitor abierto a 115200 baudios