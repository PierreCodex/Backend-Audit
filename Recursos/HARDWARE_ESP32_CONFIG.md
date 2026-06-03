# Configuración de Hardware - Nodo IoT ESP32-S3 CAM

Documento de referencia para Claude Code. Contiene toda la configuración de hardware **ya validada y funcionando** del nodo de captura del proyecto de auditoría visual de inventario. El hardware fue probado exitosamente con el ejemplo oficial CameraWebServer.

## Resumen del proyecto

Sistema IoT de auditoría visual de inventario para tienda minorista. El ESP32-S3-CAM captura imágenes de un estante de productos y las envía por WiFi a un backend Python (FastAPI) que las analiza con la API de Claude Sonnet 4.6. El backend se comunica con un sistema POS Laravel para validación cruzada y dispara notificaciones WhatsApp vía Twilio ante discrepancias.

Este documento cubre **únicamente el nodo ESP32-S3** (firmware de captura y envío). El backend Python y el POS Laravel se documentan por separado.

## Placa: ESP32-S3 WROOM N16R8 CAM

Placa de desarrollo genérica con las siguientes características confirmadas físicamente.

- **Chip:** ESP32-S3 (QFN56) revision v0.2, dual-core Xtensa LX7 @ 240MHz
- **Flash:** 16 MB
- **PSRAM:** 8 MB OPI (Octal SPI) — confirmada y detectada correctamente
- **Conectividad:** Wi-Fi 802.11 b/g/n (2.4 GHz), Bluetooth 5.0 LE
- **Puertos:** Dual USB-C (uno nativo USB OTG, uno USB-to-Serial)
- **MAC address:** 14:c1:9f:c1:b7:60 (usar como identificador único del nodo IoT)
- **Identificadores regulatorios:** FCC ID 2AB7-ESPS3N16R8, CMIIT ID 2024DC1109
- **Sensor de cámara:** OV3660 (3 megapíxeles, NO es OV2640). El cable flex viene separado y se conecta al socket FPC.

## Sensor de cámara: OV3660

- Resolución máxima: QXGA 2048x1536 (3MP)
- Compatible con la librería esp_camera de Espressif
- Detección automática del sensor disponible (PID 0x3660)
- El sensor suele venir invertido verticalmente, requiere set_vflip(s, 1)

## Perfil de cámara CORRECTO: CAMERA_MODEL_ESP32S3_EYE

**DATO CRÍTICO:** Esta placa usa el mapeo de pines del perfil **CAMERA_MODEL_ESP32S3_EYE** de la librería oficial de Espressif. Este fue el descubrimiento clave que hizo funcionar la cámara.

NO usar los pines de Freenove ni otros mapeos. El perfil ESP32S3_EYE carga automáticamente los pines correctos desde camera_pins.h.

### Pines de cámara del perfil ESP32S3_EYE (camera_pins.h de Espressif)

```cpp
#define PWDN_GPIO_NUM   -1
#define RESET_GPIO_NUM  -1
#define XCLK_GPIO_NUM   15
#define SIOD_GPIO_NUM   4
#define SIOC_GPIO_NUM   5

#define Y9_GPIO_NUM     16
#define Y8_GPIO_NUM     17
#define Y7_GPIO_NUM     18
#define Y6_GPIO_NUM     12
#define Y5_GPIO_NUM     10
#define Y4_GPIO_NUM     8
#define Y3_GPIO_NUM     9
#define Y2_GPIO_NUM     11

#define VSYNC_GPIO_NUM  6
#define HREF_GPIO_NUM   7
#define PCLK_GPIO_NUM   13
```

**NOTA IMPORTANTE:** Estos pines son los del perfil ESP32S3_EYE estándar de Espressif. Como la cámara funcionó usando ese perfil en el ejemplo CameraWebServer, estos son los pines correctos. Antes de escribir firmware nuevo, VERIFICAR estos valores abriendo el archivo camera_pins.h del ejemplo CameraWebServer en la sección `#elif defined(CAMERA_MODEL_ESP32S3_EYE)` y confirmar que coinciden, ya que pueden variar ligeramente según la versión del paquete esp32.

## Configuración Arduino IDE (validada)

Entorno de desarrollo confirmado funcionando.

- **IDE:** Arduino IDE 2.3.8
- **Paquete:** esp32 by Espressif Systems versión 3.3.8 (NO el de Arduino, el de Espressif)
- **URL del Boards Manager:** https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json

### Parámetros del menú Tools (todos validados)

| Parámetro | Valor |
|-----------|-------|
| Board | ESP32S3 Dev Module |
| USB CDC On Boot | Enabled |
| CPU Frequency | 240MHz (WiFi) |
| Core Debug Level | None |
| USB DFU On Boot | Disabled |
| Erase All Flash Before Sketch Upload | Disabled |
| Events Run On | Core 1 |
| Flash Mode | QIO 80MHz |
| Flash Size | 16MB (128Mb) |
| JTAG Adapter | Disabled |
| Arduino Runs On | Core 1 |
| USB Firmware MSC On Boot | Disabled |
| Partition Scheme | 16M Flash (3MB APP/9.9MB FATFS) |
| PSRAM | OPI PSRAM |
| Upload Mode | UART0 / Hardware CDC |
| Upload Speed | 921600 |
| USB Mode | Hardware CDC and JTAG |

**Parámetros críticos:** Flash Size en 16MB, PSRAM en OPI PSRAM. Sin estos dos, la cámara no inicializa.

## Configuración de cámara que funciona

Configuración del struct camera_config_t que funcionó en el CameraWebServer.

```cpp
camera_config_t config;
config.ledc_channel = LEDC_CHANNEL_0;
config.ledc_timer = LEDC_TIMER_0;
config.pin_d0 = Y2_GPIO_NUM;
config.pin_d1 = Y3_GPIO_NUM;
config.pin_d2 = Y4_GPIO_NUM;
config.pin_d3 = Y5_GPIO_NUM;
config.pin_d4 = Y6_GPIO_NUM;
config.pin_d5 = Y7_GPIO_NUM;
config.pin_d6 = Y8_GPIO_NUM;
config.pin_d7 = Y9_GPIO_NUM;
config.pin_xclk = XCLK_GPIO_NUM;
config.pin_pclk = PCLK_GPIO_NUM;
config.pin_vsync = VSYNC_GPIO_NUM;
config.pin_href = HREF_GPIO_NUM;
config.pin_sccb_sda = SIOD_GPIO_NUM;
config.pin_sccb_scl = SIOC_GPIO_NUM;
config.pin_pwdn = PWDN_GPIO_NUM;
config.pin_reset = RESET_GPIO_NUM;
config.xclk_freq_hz = 20000000;
config.frame_size = FRAMESIZE_UXGA;       // para el firmware de auditoria, usar SVGA o XGA
config.pixel_format = PIXFORMAT_JPEG;
config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
config.fb_location = CAMERA_FB_IN_PSRAM;
config.jpeg_quality = 12;
config.fb_count = 1;

// Con PSRAM presente (es el caso de esta placa):
if(psramFound()){
  config.jpeg_quality = 10;
  config.fb_count = 2;
  config.grab_mode = CAMERA_GRAB_LATEST;
}

// Ajustes del sensor OV3660 despues de inicializar:
sensor_t *s = esp_camera_sensor_get();
s->set_vflip(s, 1);        // el sensor viene invertido
s->set_brightness(s, 1);
s->set_saturation(s, 0);
```

## Notas de comportamiento del hardware

- **Upload:** Si el Upload se queda en "Connecting...", mantener presionado BOOT, presionar y soltar RST, soltar BOOT, y reintentar Upload. Es común con esta placa.
- **Serial Monitor:** Configurar a 115200 baudios. Tras reiniciar, el bootloader imprime mensajes ESP-ROM antes del programa.
- **LED RGB:** La placa tiene un LED RGB direccionable (WS2812) en GPIO 48. Se puede usar como indicador de estado del nodo (azul=conectando WiFi, verde=captura OK, rojo=error). Funcionalidad opcional recomendada.
- **Streaming con lag:** El streaming de video en vivo a UXGA tiene lag, pero esto es IRRELEVANTE para el proyecto, que captura fotos individuales puntuales, no video continuo.

## Problemas resueltos durante la validación (historial)

Para contexto, estos fueron los problemas que ya se resolvieron. No repetirlos.

1. **Pines incorrectos de Freenove** → daba `cam_hal: FB-OVF` en bucle. Resuelto usando perfil ESP32S3_EYE.
2. **XCLK en GPIO 0** → causaba boot loop (reinicio infinito mostrando ESP-ROM). El GPIO 0 es strapping pin, no usar para XCLK. El perfil EYE usa XCLK en 15.
3. **PSRAM mal configurada** → la cámara no inicializaba. Resuelto poniendo PSRAM en OPI PSRAM.
4. **Paquete equivocado** → primero se instaló esp32 de Arduino (sin ESP32S3 Dev Module completo). Resuelto instalando el de Espressif Systems.

## Próximos pasos del firmware (lo que falta desarrollar)

El siguiente objetivo es escribir el **firmware de producción** del nodo, que debe hacer lo siguiente.

1. **Conexión WiFi:** Conectarse a una red WiFi configurable (SSID y password). Para la demo se usará el hotspot del celular para tener red controlada.
2. **Captura periódica:** Capturar una imagen individual cada cierto intervalo configurable (ej. cada 5 minutos). NO streaming continuo.
3. **Envío HTTP POST:** Enviar la imagen capturada (JPEG) por HTTP POST al backend Python FastAPI. El endpoint del backend recibirá la imagen en base64 o como multipart/form-data.
4. **Identificación del nodo:** Incluir en cada envío el identificador único del nodo (usar la MAC 14:c1:9f:c1:b7:60 o un ID configurable).
5. **Manejo de errores y reintentos:** Si el envío falla, reintentar. Opcionalmente, guardar la imagen en la microSD como respaldo (la placa tiene slot microSD) y subirla cuando se restablezca la conexión.
6. **Indicador LED (opcional):** Usar el LED RGB del GPIO 48 para indicar estado.
7. **Modo bajo consumo (opcional):** Considerar deep sleep entre capturas para ahorro de energía si el dispositivo va a operar con batería.

### Parámetros recomendados para el firmware de auditoría

- **Resolución:** SVGA (800x600) o XGA (1024x768) es suficiente para auditoría de inventario. UXGA es innecesariamente pesado. El OV3660 soporta hasta QXGA pero no hace falta.
- **Calidad JPEG:** 10-12 (buen balance calidad/tamaño)
- **Intervalo de captura:** configurable, default 300 segundos (5 min)
- **Buffer:** fb_count 2 en PSRAM, grab_mode CAMERA_GRAB_LATEST

### Configuración de red para la demo

- Durante desarrollo: WiFi de casa
- Durante la demo/sustentación: hotspot del celular (red controlada, evita firewalls de red institucional)
- El backend Python correrá en una Mac M1 o en la misma red. El ESP32 apunta a la IP local del backend.
- El POS Laravel estará desplegado en Railway (producción cloud).

## Datos para el firmware (a completar por el usuario)

```cpp
// WiFi
const char* ssid = "______";        // nombre de la red WiFi
const char* password = "______";    // contraseña

// Backend Python
const char* backend_url = "http://192.168.X.X:8000/api/auditoria/captura";  // IP local del backend
const char* api_token = "______";   // token de autenticacion con el backend

// Identificacion del nodo
const char* nodo_id = "ESP32-14c19fc1b760";  // basado en la MAC
```

## Stack completo del proyecto (contexto general)

- **Nodo IoT:** ESP32-S3 N16R8 CAM + OV3660 (este documento) — firmware en C++/Arduino
- **Backend:** Python FastAPI — recibe imágenes, analiza con API Claude Sonnet 4.6, valida con POS
- **POS:** Laravel 12 / PHP 8.2 desplegado en Railway — endpoints REST con Sanctum, validación cruzada de ventas
- **Notificaciones:** Twilio WhatsApp API
- **Caso de uso demo:** estante de gaseosas (Coca-Cola, Inca Kola, Pepsi, Fanta, Sprite)
