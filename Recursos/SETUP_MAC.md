# Guía de instalación en macOS

Cómo dejar corriendo este proyecto en una Mac. El proyecto tiene **dos partes**:

1. **Firmware ESP32** (`sketch_may24a/`) — el código que corre en la placa ESP32-S3-CAM.
2. **Backend Python** (`backend_vision/`) — servidor FastAPI que recibe las fotos, las analiza con Claude y responde.

Para una demo básica solo necesitás las dos. El POS Laravel (XAMPP) es opcional: con `USE_MOCK_POS=true` el backend simula sus respuestas.

---

## PARTE A — Firmware ESP32 (`sketch_may24a/`)

### 1. Arduino IDE
Descargar **Arduino IDE 2.x** para macOS desde <https://www.arduino.cc/en/software> e instalarlo (arrastrar a Aplicaciones).

### 2. Soporte de placas ESP32 (Espressif)
1. Abrir **Arduino IDE → Settings…** (⌘ + ,).
2. En **Additional Boards Manager URLs**, pegar:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. **Tools → Board → Boards Manager…**, buscar **esp32** (de *Espressif Systems*) e **Install**.

Ese paquete ya incluye todo esto que usa el sketch (NO se instala aparte):
`esp_camera.h`, `esp_http_server.h`, `WiFi.h`, `HTTPClient.h`, `ESPmDNS.h`, `time.h`.
El archivo `camera_pins.h` ya viene copiado dentro de la carpeta del sketch.

### 3. Única librería externa
**Tools → Manage Libraries…**, buscar e instalar **Adafruit NeoPixel** (de *Adafruit*) — es para el LED RGB de estado.

### 4. Driver USB-serie
Según el chip USB de la placa, instalar el driver para que aparezca el puerto:
- **CP210x** (Silicon Labs) — el más común en ESP32-S3.
- o **CH340 / CH342** (WCH).

Si al conectar la placa no aparece ningún puerto en **Tools → Port**, ese es el driver que falta.

### 5. Configuración de la placa (Tools)
La placa es una **ESP32-S3 con PSRAM y cámara**, así que estos ajustes son obligatorios:
- **Board:** `ESP32S3 Dev Module`
- **PSRAM:** `OPI PSRAM` ← **sin esto la cámara NO arranca** (el código avisa con un error).
- **Partition Scheme:** una con app grande, p. ej. `Huge APP (3MB No OTA/1MB SPIFFS)`.
- **Port:** el puerto USB de la placa.

### 6. Editar credenciales antes de compilar
Abrir `sketch_may24a/secrets.h` y poner los valores propios:

| Campo | Qué poner |
|---|---|
| `WIFI_SSID` / `WIFI_PASSWORD` | Tu red WiFi (ideal: hotspot del celular para la demo). |
| `BACKEND_HOST` | La IP de la Mac en esa misma WiFi. Obtenerla con: `ipconfig getifaddr en0` |
| `BACKEND_PORT` | Dejar en `8000`. |
| `BACKEND_TOKEN` | Un token a tu elección. **Debe ser idéntico** al `ESP32_API_TOKEN` del `.env` del backend. |

> ⚠️ El `secrets.h` del repo trae credenciales de ejemplo/reales — reemplazalas por las tuyas.

Revisar también `sketch_may24a/config.h` (`NODO_ID`, intervalo de captura, etc.). Para una demo no hace falta tocar nada salvo quizás `NODO_ID`.

### 7. Compilar y subir
Botón **Upload (→)**. Tras subir, abrir el **Serial Monitor** a **115200 baudios** para ver los logs.
Mientras esté conectado a la WiFi podés ver el stream en vivo en: `http://esp32-cam.local/`

---

## PARTE B — Backend Python (`backend_vision/`)

### 1. Python ≥ 3.11
```bash
brew install python@3.11
python3 --version          # confirmar 3.11 o superior
```

### 2. Entorno virtual + dependencias
```bash
cd ruta/al/proyecto/backend_vision

python3 -m venv .venv
source .venv/bin/activate          # activar el venv (en Mac/zsh)

pip install -r requirements.txt
```

Esto instala: `fastapi`, `uvicorn`, `anthropic`, `httpx`, `pydantic`, `pydantic-settings`,
`python-dotenv`, `python-multipart`, `structlog`, `tenacity`, `pytest`, `pytest-asyncio`.

### 3. Crear el `.env`
```bash
cp .env.example .env
```
Editar `.env` y completar como mínimo:

| Variable | Valor |
|---|---|
| `ANTHROPIC_API_KEY` | Tu API key de <https://console.anthropic.com> |
| `ESP32_API_TOKEN` | **El mismo** que pusiste en `BACKEND_TOKEN` del `secrets.h`. |
| `USE_MOCK_POS` | `true` ← recomendado para demo (no requiere el POS Laravel corriendo). |

### 4. Correr el backend
```bash
export PYTHONPATH="$PWD/src"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Verificar:
- Health: <http://localhost:8000/api/v1/health>
- Docs:   <http://localhost:8000/docs>

> El ESP32 envía a la **IP de la Mac** (lo que pusiste en `BACKEND_HOST`), no a `localhost`.
> Si el ESP32 no logra conectar, revisar que el **firewall de macOS** permita conexiones
> entrantes al puerto 8000 (System Settings → Network → Firewall).

### 5. (Opcional) Tests
```bash
export PYTHONPATH="$PWD/src"
pytest                 # todos
pytest tests/unit      # solo unit (rápido, sin red)
```

---

## Alternativa con Docker (sin instalar Python)
El backend trae un `Dockerfile`. Con Docker Desktop instalado:
```bash
cd backend_vision
docker build -t backend-vision .
docker run --rm -p 8000:8000 --env-file .env backend-vision
```
(Igual necesitás el `.env` configurado del paso B.3.)

---

## Resumen mínimo
1. **Firmware:** Arduino IDE + paquete `esp32` (Espressif) + librería **Adafruit NeoPixel** + driver USB-serie. Editar `secrets.h`. Board = ESP32S3 Dev Module con **PSRAM = OPI PSRAM**.
2. **Backend:** Python ≥3.11 → venv → `pip install -r requirements.txt` → `cp .env.example .env` (poner `ANTHROPIC_API_KEY`, `ESP32_API_TOKEN`, `USE_MOCK_POS=true`) → `uvicorn`.
3. El `ESP32_API_TOKEN` del backend y el `BACKEND_TOKEN` del firmware **tienen que ser iguales**.