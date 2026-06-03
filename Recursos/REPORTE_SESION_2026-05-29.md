# Reporte de sesión — 2026-05-29

Sesión de depuración del nodo ESP32-S3-CAM ↔ Backend Python. **El pipeline completo
quedó funcionando** (captura → backend → Claude → POS, HTTP 201). Queda pendiente solo
el stream en vivo (enlace WiFi inestable) y enfocar la cámara con buena luz.

---

## 1. Resumen ejecutivo — qué se logró

- ✅ **Se encontró la causa raíz por la que "nada llegaba al backend": el Firewall de
  Windows** bloqueaba el puerto 8000. Se creó la regla y **ahora la captura llega y Claude
  responde** (HTTP 201, `auditoria_id_pos` asignado).
- ✅ Se bajó la resolución **UXGA → XGA** (UXGA saturaba el módulo: `send payload failed`
  + `cam_hal: FB-OVF`).
- ✅ Se estabilizó el **stream**: dos servidores HTTP separados (página en :80, stream en
  :81) + `WiFi.setSleep(false)` + `fb_count=3`. La **página ya carga** y no se cuelga.
- ✅ Se montó flujo de trabajo con **arduino-cli** (compilar/subir/leer Serial directo).
- ⚠️ **Stream en vivo todavía no entrega imagen de forma confiable** — el enlace WiFi
  ESP32↔PC pierde paquetes (sospecha: adaptador WiFi USB TP-Link de la PC en puerto USB 3.0
  → interferencia 2.4 GHz). NO es problema de firmware.
- ⚠️ **Imagen oscura** de noche → Claude cuenta 0. Se resuelve con luz física (lo hace el user).

---

## 2. Causas raíz encontradas (diagnóstico)

| Síntoma | Causa real | Estado |
|---|---|---|
| LED rojo, "nada llega al backend" | **Firewall de Windows** bloqueaba inbound TCP 8000 (Wi-Fi perfil Public) | ✅ Resuelto con regla netsh |
| `send payload failed` + `cam_hal: FB-OVF` | **UXGA** (226 KB) satura PSRAM/heap con WiFi+stream | ✅ Resuelto bajando a XGA |
| No aparecía la URL en Serial Monitor | **USB CDC On Boot = Enabled** mandaba el Serial al USB nativo; la placa usa chip **CH343** (COM3) | ✅ Resuelto con CDC On Boot = **Disabled** |
| Stream colgaba la página entera | El stream MJPEG (bucle infinito) ocupaba el **único worker** del server | ✅ Resuelto con server aparte en puerto 81 |
| Stream no entrega imagen / ping con pérdida | **Enlace WiFi lossy** pese a señal -45 dBm (sospecha: adaptador USB TP-Link / USB 3.0) | ⚠️ Pendiente (físico, no firmware) |
| Claude cuenta 0 productos | **Imagen oscura** (de noche, sin luz) | ⚠️ Pendiente (luz física) |

---

## 3. Estado actual del sistema

```
ESP32-S3-CAM (192.168.1.18)          PC (192.168.1.9)              Claude / POS
   ✅ flasheado y corriendo    →    ✅ Backend uvicorn :8000   →   ✅ responde 201
   ✅ captura cada 5 min             ✅ Firewall regla OK            cantidad_total varía
   ✅ POST llega (XGA ~40-90KB)      ✅ guarda en storage/debug      según luz de la escena
   ⚠️ stream :81 inestable
```

- **Firmware en la placa AHORA:** XGA, doble servidor (:80 página, :81 stream),
  `setSleep(false)`, `fb_count=3`, warm-up 3 frames, sensor settings completos.
- **Pipeline de auditoría:** funciona de punta a punta.
- **IPs (DHCP, pueden cambiar):** PC = `192.168.1.9`, ESP32 = `192.168.1.18`.

---

## 4. Comandos

### 4.1 Levantar el backend (uvicorn)

```powershell
cd F:\PERSONAL_JEAN\project-arduino\backend_vision
# El --host 0.0.0.0 es OBLIGATORIO (si no, el ESP32 no llega). El --app-dir src
# es porque el objeto app vive en src/main.py.
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --app-dir src
```

Verificar que levantó:
- Health: http://localhost:8000/api/v1/health  → debe dar `{"status":"ok",...}`
- Swagger: http://localhost:8000/docs

> Nota: el `.venv` ya tiene las dependencias (structlog, fastapi, anthropic, etc.).
> Usar `.\.venv\Scripts\python.exe -m uvicorn` evita depender de activar el venv.

### 4.2 Regla de firewall (YA está creada, solo si reaparece el bloqueo)

Si el LED vuelve a rojo con "connection refused" y el backend está OK, revisar/recrear
la regla (PowerShell **como administrador**):

```powershell
netsh advfirewall firewall add rule name="Backend Vision ESP32 8000" dir=in action=allow protocol=TCP localport=8000 profile=any
# Verificar:
netsh advfirewall firewall show rule name="Backend Vision ESP32 8000"
```

> Importante: `New-NetFirewallRule` (cmdlet) falló en silencio en esta máquina; usar `netsh`.

### 4.3 Verificar conectividad rápida

```powershell
# IP actual de la PC (debe coincidir con BACKEND_HOST de secrets.h)
ipconfig | Select-String "IPv4"
# Backend escuchando?
Get-NetTCPConnection -State Listen -LocalPort 8000
# IP del ESP32
ping esp32-cam.local
```

### 4.4 Compilar / subir el firmware con arduino-cli (sin Arduino IDE)

```powershell
# Compilar
arduino-cli compile "F:\PERSONAL_JEAN\project-arduino\sketch_may24a" --fqbn "esp32:esp32:esp32s3:PSRAM=opi,FlashSize=16M,CDCOnBoot=default,PartitionScheme=huge_app"
# Subir (placa en COM3)
arduino-cli upload "F:\PERSONAL_JEAN\project-arduino\sketch_may24a" -p COM3 --fqbn "esp32:esp32:esp32s3:PSRAM=opi,FlashSize=16M,CDCOnBoot=default,PartitionScheme=huge_app"
# Ver Serial
arduino-cli monitor -p COM3 -c baudrate=115200
```

### 4.5 Ver el conteo de Claude (sin POS)

El endpoint solo devuelve el resumen (`cantidad_total`, `confianza_general`). Para ver el
**desglose por producto** que hace Claude, usar el script `ver_conteo.py`:

```powershell
cd F:\PERSONAL_JEAN\project-arduino\backend_vision
# Sobre la captura mas reciente de storage/debug/:
.\.venv\Scripts\python.exe ver_conteo.py
# O sobre una imagen especifica:
.\.venv\Scripts\python.exe ver_conteo.py ruta\a\imagen.jpg
```

Imprime cada producto (nombre, cantidad, confianza), total, confianza general, espacios
vacios y las **observaciones** de Claude (muy utiles para saber por que cuenta poco —
ej. "imagen oscura/desenfocada"). No necesita el backend levantado, solo internet + la
API key del `.env`.

Alternativa rapida sin script: **Swagger** (http://localhost:8000/docs) o **Postman** →
`POST /api/v1/auditoria/captura` con la imagen → la respuesta trae `cantidad_total` y
`confianza_general` (pero no el desglose por producto).

### 4.6 Control de costos de tokens (IMPORTANTE)

Por defecto, **cada foto del ESP32 se manda a Claude automaticamente** (consume tokens,
~288/dia con captura cada 5 min). Para pruebas, hay un flag nuevo en `.env`:

```
ANALISIS_AUTOMATICO=false   # guarda la imagen pero NO llama a Claude (no gasta tokens)
ANALISIS_AUTOMATICO=true    # flujo real: ESP32 -> Claude -> POS
```

- Con `false` (estado actual): el ESP32 captura, el backend **guarda** en `storage/debug/`
  y devuelve 201 (LED verde), pero **no analiza**. Vos elegis que imagen analizar con
  `python ver_conteo.py <imagen>`.
- Con `true`: análisis automatico en cada captura.
- **Cambiar el `.env` requiere reiniciar uvicorn** (Ctrl+C y volver a levantar).

---

## 5. Archivos de Arduino (los que se flashean)

**Son 4 archivos en una sola carpeta** (sketch de Arduino). Hay DOS copias sincronizadas
(idénticas tras esta sesión):

- Carpeta de trabajo (Arduino IDE): `C:\Users\pierr\Desktop\arduino\sketch_may24a\`
- Copia versionada en el proyecto:   `F:\PERSONAL_JEAN\project-arduino\sketch_may24a\`

| Archivo | Qué tiene |
|---|---|
| `sketch_may24a.ino` | Sketch principal (cámara, WiFi, NTP, captura+POST, doble servidor stream) |
| `config.h` | Constantes: `FRAMESIZE_AUDITORIA = FRAMESIZE_XGA`, calidad, timeouts, mDNS |
| `secrets.h` | `WIFI_SSID="CORDOVA 2.4G"`, `BACKEND_HOST="192.168.1.9"`, `BACKEND_TOKEN` |
| `camera_pins.h` | Pines de la cámara (perfil ESP32S3_EYE, viene del ejemplo CameraWebServer) |

### Config OBLIGATORIA en Arduino IDE (Tools)
- **Board:** ESP32S3 Dev Module
- **PSRAM:** `OPI PSRAM`
- **Flash Size:** `16MB (128Mb)`
- **Partition Scheme:** `Huge APP (3MB No OTA/1MB SPIFFS)`  ← sin esto NO entra el binario
- **USB CDC On Boot:** `Disabled`  ← para ver el Serial por COM3 (chip CH343)
- **Puerto:** COM3

> ⚠️ El sketch documentado viejo en `firmware_esp32/FIRMWARE_ESP32_CODIGO.md` quedó
> DESACTUALIZADO (dice UXGA, un solo servidor). **La fuente de verdad es la carpeta
> `sketch_may24a/`**, no ese MD.

---

## 6. Lo que falta (próximos pasos)

1. **Enfocar la cámara (opción B — sin stream, confiable):**
   - Apuntar al estante **con luz** → apretar RST en la placa → la foto cae en
     `backend_vision/storage/debug/` → revisar nitidez → girar aro del lente → repetir.
2. **Resolver el stream en vivo (opcional):** mover el adaptador WiFi USB TP-Link a un
   **puerto USB 2.0** o usar alargador (alejarlo de puertos USB 3.0). Recargar
   `http://192.168.1.18/`. Si en el **celular** (misma red 2.4 GHz) carga → es el adaptador del PC.
3. **Subir resolución gradualmente** una vez estable y con luz: XGA → SXGA → UXGA,
   validando en cada paso (sin volver a saturar).
4. **Integración:** conectar POS real (`USE_MOCK_POS=false`), token del POS, end-to-end.
5. **Ajustes del POS** (`POS_AJUSTES_PENDIENTES.md`) y deploy a Railway.

---

## 7. Datos técnicos clave (para no re-descubrir)

- Placa: ESP32-S3 N16R8, OV3660 (**sin autofocus** — foco manual con el aro del lente).
- Chip USB-serial: **CH343** (VID 0x1A86) en **COM3**.
- MAC: `14:c1:9f:c1:b7:60` (= `NODO_ID` en config.h).
- 8 MB PSRAM OPI, 16 MB flash. El sketch pesa ~1.18 MB → requiere partition `huge_app`.
- ESP32-S3 solo usa **WiFi 2.4 GHz** (no 5 GHz).
- Backend token actual: `cambiar_por_token_seguro` (coincide con `ESP32_API_TOKEN` del `.env`).
- LED RGB: azul=conectando, verde=captura OK, amarillo=sin WiFi, rojo=error backend.