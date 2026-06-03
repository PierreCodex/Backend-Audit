# Sketch temporal: ajustar el foco del OV3660

El OV3660 **no tiene autofocus** — el foco se ajusta a mano girando el aro plástico del lente. Este sketch levanta un stream MJPEG en el navegador para hacer ese ajuste con feedback en tiempo real.

Después de enfocar, **no toques más el aro** y volvé a flashear el firmware de auditoría (`FIRMWARE_ESP32_CODIGO.md`).

## Modo: AP (Access Point)

El ESP32 **crea su propia red WiFi** llamada `ESP32-ENFOQUE`. Tu PC se conecta directo a esa red (no necesitás router ni hotspot del celular). La IP es siempre **`192.168.4.1`** — fija y garantizada.

**Ventajas:**
- Cero problemas de modem-sleep / WiFi inestable
- Cero búsqueda de IP con `arp`
- Señal fuertísima (estás al lado de la placa)
- No depende de que tu router/hotspot esté prendido

**Limitación temporal:** mientras tu PC esté conectada al WiFi del ESP32, no vas a tener internet. Pero son 5 minutos para enfocar.

---

## Estructura del sketch

Solo **2 archivos** en una carpeta nueva llamada `firmware_enfoque/`:

1. `firmware_enfoque.ino` — sketch principal (las credenciales del AP están inline)
2. `camera_pins.h` — el mismo que usaste en `firmware_esp32/` (copialo tal cual)

> Nota: en modo AP no hace falta `secrets_enfoque.h` porque el ESP32 no se conecta a ninguna red existente, solo crea la suya propia con credenciales fijas.

> El `.ino` debe estar dentro de una carpeta con el **mismo nombre** (sin extensión). Los `.h` van en la misma carpeta y se cargan automáticamente como pestañas del sketch.

---

## 1. `firmware_enfoque.ino`

```cpp
/*
 * Sketch temporal — ajuste de foco del OV3660 (modo AP)
 *
 * El ESP32 crea su propia red WiFi "ESP32-ENFOQUE" (pass: 12345678).
 * Conectá tu PC a esa red y abrí http://192.168.4.1/ en Chrome.
 *
 * Sirve:
 *   GET /        → HTML con <img src="/stream">
 *   GET /stream  → MJPEG continuo a ~15 fps
 *
 * Usá esto para girar el aro del lente mirando el navegador hasta que la
 * imagen se vea nítida a la distancia real del estante. Después flashea el
 * firmware de auditoría sin tocar más el aro.
 */

#define CAMERA_MODEL_ESP32S3_EYE

#include "esp_camera.h"
#include "esp_http_server.h"
#include "camera_pins.h"
#include <WiFi.h>
#include <Adafruit_NeoPixel.h>

// ============================================================================
// Credenciales del Access Point creado por el ESP32
// ============================================================================
#define AP_SSID      "ESP32-ENFOQUE"
#define AP_PASSWORD  "12345678"     // mínimo 8 caracteres si querés WPA2

// ============================================================================
// LED RGB (mismo pin que el firmware de auditoría)
// ============================================================================
#define LED_RGB_PIN  48
#define LED_BRILLO   32

Adafruit_NeoPixel led(1, LED_RGB_PIN, NEO_GRB + NEO_KHZ800);

void ledColor(uint8_t r, uint8_t g, uint8_t b) {
  led.setPixelColor(0, led.Color(r, g, b));
  led.show();
}
void ledAzul()  { ledColor(0, 0, LED_BRILLO); }              // streaming
void ledVerde() { ledColor(0, LED_BRILLO, 0); }              // cliente conectado
void ledRojo()  { ledColor(LED_BRILLO, 0, 0); }              // error

// ============================================================================
// Cámara — VGA para fluidez en el stream (~15 fps).
// La nitidez del foco se evalúa igual de bien a VGA que a UXGA.
// Los sensor settings son los MISMOS que el firmware de auditoría, así el
// foco se ajusta sobre la configuración real.
// ============================================================================
bool inicializarCamara() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.frame_size   = FRAMESIZE_VGA;     // 640x480 para stream fluido
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode    = CAMERA_GRAB_LATEST;
  config.fb_location  = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12;
  config.fb_count     = 2;

  if (!psramFound()) {
    Serial.println("[CAM] ERROR: PSRAM no detectada — revisar Tools > PSRAM = OPI PSRAM");
    return false;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[CAM] Init falló con error 0x%x\n", err);
    return false;
  }

  // Mismos settings que el firmware de auditoría
  sensor_t *s = esp_camera_sensor_get();
  if (s) {
    s->set_vflip(s, 1);
    s->set_hmirror(s, 0);
    s->set_brightness(s, 0);
    s->set_contrast(s, 1);
    s->set_saturation(s, 0);
    s->set_sharpness(s, 2);
    s->set_denoise(s, 1);
    s->set_exposure_ctrl(s, 1);
    s->set_aec2(s, 1);
    s->set_ae_level(s, 0);
    s->set_gain_ctrl(s, 1);
    s->set_gainceiling(s, GAINCEILING_4X);
    s->set_whitebal(s, 1);
    s->set_awb_gain(s, 1);
    s->set_wb_mode(s, 0);
    s->set_lenc(s, 1);
    s->set_bpc(s, 1);
    s->set_wpc(s, 1);
    s->set_raw_gma(s, 1);
  }

  Serial.println("[CAM] OK (VGA streaming)");
  return true;
}

// ============================================================================
// WiFi en modo Access Point — el ESP32 crea su propia red
// ============================================================================
bool iniciarAP() {
  Serial.printf("[AP] Creando red \"%s\"...\n", AP_SSID);
  WiFi.mode(WIFI_AP);

  bool ok = WiFi.softAP(AP_SSID, AP_PASSWORD);
  if (!ok) {
    Serial.println("[AP] softAP() falló");
    return false;
  }

  IPAddress ip = WiFi.softAPIP();
  Serial.printf("[AP] OK. SSID=%s  IP=%s\n", AP_SSID, ip.toString().c_str());
  return true;
}

// ============================================================================
// Servidor HTTP — MJPEG en /stream, HTML simple en /
// ============================================================================
httpd_handle_t servidor = NULL;

static const char* MJPEG_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=frame";
static const char* MJPEG_BOUNDARY     = "\r\n--frame\r\n";
static const char* MJPEG_PART_HEADER  = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

static const char INDEX_HTML[] PROGMEM = R"HTML(
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>OV3660 — Ajuste de foco</title>
<style>
  body { margin:0; background:#111; color:#eee; font-family:system-ui,sans-serif; text-align:center; }
  h1 { font-size:18px; margin:8px 0; font-weight:500; }
  p  { font-size:13px; margin:4px 0; opacity:.75; }
  img { max-width:100%; height:auto; display:block; margin:0 auto; border:1px solid #333; }
</style>
</head>
<body>
<h1>OV3660 — Stream para ajuste de foco</h1>
<p>Girá el aro del lente lento. Cuando el texto/los bordes se vean nítidos, ¡listo!</p>
<img src="/stream" alt="stream">
</body>
</html>
)HTML";

static esp_err_t index_handler(httpd_req_t *req) {
  ledVerde();
  httpd_resp_set_type(req, "text/html");
  return httpd_resp_send(req, INDEX_HTML, strlen(INDEX_HTML));
}

static esp_err_t stream_handler(httpd_req_t *req) {
  ledVerde();
  esp_err_t res = httpd_resp_set_type(req, MJPEG_CONTENT_TYPE);
  if (res != ESP_OK) return res;

  char part_buf[64];
  while (true) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
      res = ESP_FAIL;
      break;
    }
    res = httpd_resp_send_chunk(req, MJPEG_BOUNDARY, strlen(MJPEG_BOUNDARY));
    if (res == ESP_OK) {
      size_t hlen = snprintf(part_buf, sizeof(part_buf), MJPEG_PART_HEADER, fb->len);
      res = httpd_resp_send_chunk(req, part_buf, hlen);
    }
    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
    }
    esp_camera_fb_return(fb);
    if (res != ESP_OK) break;
    delay(50);  // ~15-20 fps efectivos
  }
  ledAzul();
  return res;
}

void iniciarServidor() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;
  config.stack_size  = 8192;

  httpd_uri_t uri_index  = { .uri = "/",       .method = HTTP_GET, .handler = index_handler,  .user_ctx = NULL };
  httpd_uri_t uri_stream = { .uri = "/stream", .method = HTTP_GET, .handler = stream_handler, .user_ctx = NULL };

  if (httpd_start(&servidor, &config) == ESP_OK) {
    httpd_register_uri_handler(servidor, &uri_index);
    httpd_register_uri_handler(servidor, &uri_stream);
    Serial.println("[HTTP] Servidor en puerto 80 listo");
  } else {
    Serial.println("[HTTP] No se pudo iniciar el servidor");
    ledRojo();
  }
}

// ============================================================================
// SETUP / LOOP
// ============================================================================
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n\n=== Sketch de ajuste de foco — OV3660 ===");

  led.begin();
  led.setBrightness(255);
  ledAzul();

  if (!inicializarCamara()) {
    ledRojo();
    delay(10000);
    ESP.restart();
  }
  if (!iniciarAP()) {
    ledRojo();
    delay(10000);
    ESP.restart();
  }

  iniciarServidor();
  ledAzul();

  Serial.println();
  Serial.println("==========================================================");
  Serial.println("  1) Conectá tu PC a la red WiFi:");
  Serial.printf("       SSID: %s\n", AP_SSID);
  Serial.printf("       Pass: %s\n", AP_PASSWORD);
  Serial.println("  2) Abrí en Chrome:  http://192.168.4.1/");
  Serial.println("  3) Girá el aro del lente del OV3660 hasta ver nítido.");
  Serial.println("  4) Después flashea FIRMWARE_ESP32_CODIGO.md sin tocar el aro.");
  Serial.println("==========================================================");
}

void loop() {
  // En modo AP el ESP32 ES la red, no se "desconecta" como un cliente STA.
  // Solo logueamos cuántas estaciones están conectadas para feedback.
  static unsigned long ultimoLog = 0;
  if (millis() - ultimoLog > 5000) {
    Serial.printf("[AP] Estaciones conectadas: %d\n", WiFi.softAPgetStationNum());
    ultimoLog = millis();
  }
  delay(1000);
}
```

---

## 2. `camera_pins.h`

Copia el **mismo archivo** que ya tenés en `firmware_esp32/camera_pins.h` (lo agregaste manualmente con las definiciones de pins del `CAMERA_MODEL_ESP32S3_EYE`).

---

## Procedimiento de enfoque (paso a paso)

1. **Crear** la carpeta `firmware_enfoque/` en algún lado (puede ser dentro del proyecto o en `Documentos/Arduino/`).
2. **Crear** los 2 archivos arriba (`.ino`, `camera_pins.h`) dentro de esa carpeta.
3. **Abrir** `firmware_enfoque.ino` en Arduino IDE → `camera_pins.h` aparece como pestaña.
4. **Configuración del board** (igual que el firmware de auditoría):
   - Tools > Board: ESP32S3 Dev Module
   - Tools > PSRAM: OPI PSRAM
   - Tools > Flash Size: 16MB
   - Tools > Partition Scheme: 16M Flash (3MB APP/9.9MB FATFS)
5. **Conectar** el ESP32 por USB, seleccionar el puerto correcto.
6. **Compilar y subir** (botón Upload o Ctrl+U).
7. (Opcional) **Abrir Serial Monitor** (115200 baud) para ver:
   ```
   [AP] OK. SSID=ESP32-ENFOQUE  IP=192.168.4.1
   ```
   Si no ves Serial output pero el LED queda en **azul fijo**, el AP igual está corriendo.
8. **En tu PC**: click en el ícono de WiFi (abajo derecha) y conectate a la red:
   - SSID: `ESP32-ENFOQUE`
   - Pass:  `12345678`
   Windows te va a avisar "Sin internet" — es normal, esa WiFi solo sirve para hablar con el ESP32.
9. **Abrir Chrome** y navegar a: `http://192.168.4.1/`
10. Debería aparecer la página con el stream MJPEG en vivo. El LED del ESP32 cambia a **verde** mientras hay cliente conectado.
11. **Apuntar la cámara** al estante a la distancia real (típicamente 30-50 cm).
12. **Girar el aro del lente** lento (1/8 de vuelta por vez) mirando el stream:
    - Si está muy fuera de foco, girá una vuelta entera para empezar.
    - Cuando los bordes y el texto se vean filosos, parate.
    - El lente puede tener una **mini tuerca de bloqueo** detrás del aro — si la sentís dura, no fuerces.
13. **Verificar** mirando los detalles más pequeños del estante (etiquetas, códigos, esquinas de productos). Deben ser legibles.
14. **No tocar más el aro**.
15. **Reconectar tu PC** a la WiFi normal (`CORDOVA 5G` o la que uses).

---

## Volver al firmware de auditoría

1. En Arduino IDE: File > Open → seleccionar `firmware_esp32/firmware_esp32.ino`.
2. Compilar y subir.
3. El ESP32 vuelve a capturar cada 5 minutos con la nueva config (UXGA + sensor settings mejorados).
4. Ver la nueva captura en `backend_vision/storage/debug/` — debería pesar ~150-250 KB y verse nítida.

---

## Troubleshooting

- **No aparece `ESP32-ENFOQUE` en la lista de WiFi de mi PC**: el sketch no arrancó. Revisar LED — si está rojo, falló cámara o softAP. Si está apagado, no se ejecutó. Reset (botón RST) y volver a probar. Si persiste, revisar config del board (PSRAM = OPI PSRAM).
- **Conecto al WiFi del ESP32 pero `192.168.4.1` no carga**: verificar que la PC realmente quedó en la red `ESP32-ENFOQUE` (Windows a veces vuelve sola a la red anterior si dice "Sin internet"). En PowerShell: `ipconfig | findstr "IPv4"` — deberías ver una IP en rango `192.168.4.X`.
- **El stream se traba o se ve lento**: bajá `delay(50)` a `delay(100)` en `stream_handler`. También probá acercar la PC a la placa.
- **Imagen siempre borrosa por más que gires el aro**: revisá que el lente no tenga el plástico protector adherido, y que esté limpio (paño con alcohol isopropílico).
- **Stream funciona pero el firmware de auditoría sigue dando capturas borrosas**: probable que reflasheaste y volviste a girar el aro sin querer al manipular la placa. Repetir el procedimiento.
- **Mi PC dice "Sin internet" al conectar a ESP32-ENFOQUE**: es lo esperado. El ESP32 no es un router con salida a internet, solo es un AP local para hablar con tu PC. Para volver a tener internet, reconectá a tu WiFi normal.
