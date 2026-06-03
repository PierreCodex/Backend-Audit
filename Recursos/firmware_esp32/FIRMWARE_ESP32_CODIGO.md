# Código del firmware ESP32-S3-CAM

Tres archivos para pegar en el Arduino IDE dentro de una carpeta llamada `firmware_esp32`:

1. `firmware_esp32.ino` — sketch principal
2. `secrets.h` — credenciales WiFi y tokens (NO commitear)
3. `config.h` — constantes ajustables

> El Arduino IDE requiere que el archivo `.ino` esté dentro de una carpeta con el **mismo nombre** (sin extensión). Los `.h` van en la misma carpeta y se cargan automáticamente como pestañas del sketch.

Setup completo paso a paso → ver `FIRMWARE_ESP32_SETUP.md`.

---

## 1. `secrets.h` — tus credenciales (NO commitear)

Crea este archivo PRIMERO. Reemplazá los `XXX` con tus valores reales.

```cpp
#pragma once

// ============================================================================
// WiFi — usar el hotspot del celular para la demo (red controlada)
// ============================================================================
#define WIFI_SSID      "CORDOVA 2.4G"
#define WIFI_PASSWORD  "73MC8217"

// ============================================================================
// Backend Python — IP local de tu Mac/PC en la WiFi del hotspot
// ============================================================================
// Cómo obtenerla:
//   Windows: abrir CMD/PowerShell y correr `ipconfig`, buscar la sección de
//            "Adaptador de LAN inalámbrica Wi-Fi" → IPv4
//   macOS:   abrir Terminal y correr `ipconfig getifaddr en0`
//   Linux:   `hostname -I`
//
// Ejemplo: si tu Mac tiene 192.168.43.123, queda:
//   #define BACKEND_HOST  "192.168.43.123"
// El puerto SIEMPRE es 8000 (el del uvicorn).
#define BACKEND_HOST   "192.168.1.9"
#define BACKEND_PORT   8000

// ============================================================================
// Token de auth del backend (debe coincidir con ESP32_API_TOKEN del .env)
// ============================================================================
#define BACKEND_TOKEN  "cambiar_por_token_seguro"
```

---

## 2. `config.h` — constantes del firmware

```cpp
#pragma once

// ============================================================================
// Identificación del nodo
// ============================================================================
// La MAC de TU placa específica (validada en HARDWARE_ESP32_CONFIG.md).
// El backend Python valida que tenga >= 12 chars en NodoId.
#define NODO_ID  "14:c1:9f:c1:b7:60"

// ============================================================================
// Captura
// ============================================================================
#define INTERVALO_CAPTURA_MS  (5 * 60 * 1000UL)  // 5 minutos

// Resolución de la imagen — XGA (1024x768, ~0.8 MP) es el punto estable:
// ~2.5x más nítido que SVGA pero liviano en memoria, corriente y ancho de
// banda. UXGA (1600x1200) resultó demasiado para el módulo: capturas fallidas
// (LED rojo) y stream que no carga, probablemente por consumo de corriente y
// contención de cámara con el stream. Si XGA va estable y querés más nitidez,
// subir de a un paso: XGA → SXGA (1280x1024) → UXGA, validando en cada nivel.
// Opciones del OV3660: FRAMESIZE_VGA (640x480), FRAMESIZE_SVGA (800x600),
//                      FRAMESIZE_XGA (1024x768), FRAMESIZE_SXGA (1280x1024),
//                      FRAMESIZE_UXGA (1600x1200), FRAMESIZE_QXGA (2048x1536)
#define FRAMESIZE_AUDITORIA   FRAMESIZE_XGA

// Calidad JPEG: 0-63 (menor = mejor calidad, archivo más grande). 10 es el
// mejor valor razonable sin que el archivo crezca demasiado.
#define CALIDAD_JPEG          10

// ============================================================================
// HTTP
// ============================================================================
#define HTTP_TIMEOUT_MS       30000   // 30s — Claude puede tardar
#define HTTP_REINTENTOS_MAX   3
#define HTTP_BACKOFF_BASE_MS  2000    // 2s, 4s, 8s

// Tipo de evento que se envía al backend
// Opciones: "auditoria_apertura" | "rutina" | "reposicion" | "discrepancia"
#define TIPO_EVENTO_DEFAULT   "rutina"

// ============================================================================
// NTP — zona horaria Perú (Lima)
// ============================================================================
#define NTP_OFFSET_SEGUNDOS   (-5 * 3600)  // UTC-5
#define NTP_DST_OFFSET        0             // Perú no usa horario de verano
#define NTP_SERVER_1          "pool.ntp.org"
#define NTP_SERVER_2          "time.nist.gov"

// ============================================================================
// LED RGB de estado (WS2812 en GPIO 48 — confirmado en HARDWARE_ESP32_CONFIG.md)
// ============================================================================
#define LED_RGB_PIN           48
#define LED_BRILLO            32  // 0-255 (32 es suave, no encandila)

// ============================================================================
// Stream en vivo + mDNS — para inspeccionar/enfocar sin reflashear
// Mientras el ESP32 esté en la WiFi, podés abrir en Chrome:
//   http://esp32-cam.local/   (mDNS, recomendado)
//   http://<ip-del-esp32>/    (fallback si mDNS no funciona)
// ============================================================================
#define HOSTNAME_MDNS         "esp32-cam"
```

---

## 3. `firmware_esp32.ino` — sketch principal

```cpp
/*
 * Firmware nodo IoT — Auditoría visual de inventario
 *
 * Placa:    ESP32-S3 WROOM N16R8 CAM
 * Cámara:   OV3660 (perfil CAMERA_MODEL_ESP32S3_EYE)
 * MAC:      14:c1:9f:c1:b7:60
 *
 * Flujo:
 *   1. Conecta a WiFi (LED azul)
 *   2. Sincroniza hora vía NTP
 *   3. Inicializa cámara (UXGA 1600x1200, JPEG quality 10)
 *   4. Levanta servidor HTTP local para stream en vivo:
 *        http://esp32-cam.local/        → HTML con stream MJPEG
 *        http://esp32-cam.local/stream  → MJPEG continuo (para enfocar/inspeccionar)
 *   5. Cada 5 minutos: captura JPEG → POST multipart al backend Python
 *      con headers Authorization, X-Nodo-Id, X-Timestamp, X-Request-Id, X-Tipo-Evento
 *   6. Indica resultado por LED RGB (verde OK / rojo error / amarillo sin WiFi)
 *
 * Setup Arduino IDE: ver FIRMWARE_ESP32_SETUP.md
 */

#define CAMERA_MODEL_ESP32S3_EYE  // perfil oficial validado

#include "esp_camera.h"
#include "esp_http_server.h"
#include "camera_pins.h"   // viene con el ejemplo CameraWebServer del paquete esp32
#include <WiFi.h>
#include <HTTPClient.h>
#include <ESPmDNS.h>
#include <time.h>
#include <Adafruit_NeoPixel.h>

#include "secrets.h"
#include "config.h"

// ============================================================================
// LED RGB
// ============================================================================
Adafruit_NeoPixel led(1, LED_RGB_PIN, NEO_GRB + NEO_KHZ800);

void ledColor(uint8_t r, uint8_t g, uint8_t b) {
  led.setPixelColor(0, led.Color(r, g, b));
  led.show();
}
void ledAzul()     { ledColor(0, 0, LED_BRILLO); }       // conectando WiFi / NTP
void ledVerde()    { ledColor(0, LED_BRILLO, 0); }       // captura enviada OK
void ledAmarillo() { ledColor(LED_BRILLO, LED_BRILLO, 0); } // sin WiFi
void ledRojo()     { ledColor(LED_BRILLO, 0, 0); }       // error backend
void ledApagado()  { ledColor(0, 0, 0); }

// ============================================================================
// Cámara — inicialización siguiendo HARDWARE_ESP32_CONFIG.md
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
  config.frame_size   = FRAMESIZE_AUDITORIA;
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode    = CAMERA_GRAB_LATEST;
  config.fb_location  = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = CALIDAD_JPEG;
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

  // Ajustes del OV3660 — el sensor NO tiene autofocus (eso es del OV5640).
  // El foco se ajusta físicamente girando el aro del lente. Estos settings
  // maximizan la nitidez perceptible y dan margen al sensor para compensar
  // variaciones de iluminación entre capturas cada 5 minutos.
  sensor_t *s = esp_camera_sensor_get();
  if (s) {
    // --- Orientación (OV3660 viene físicamente invertido en el módulo) ---
    s->set_vflip(s, 1);
    s->set_hmirror(s, 0);

    // --- Calidad de imagen (rango -2..+2, salvo denoise: 0/1) ---
    s->set_brightness(s, 0);
    s->set_contrast(s, 1);
    s->set_saturation(s, 0);
    s->set_sharpness(s, 2);   // máximo: contrarresta la suavidad del lente plástico
    s->set_denoise(s, 1);

    // --- Exposición y ganancia automáticas ---
    s->set_exposure_ctrl(s, 1);
    s->set_aec2(s, 1);
    s->set_ae_level(s, 0);
    s->set_gain_ctrl(s, 1);
    s->set_gainceiling(s, GAINCEILING_4X);

    // --- White balance automático ---
    s->set_whitebal(s, 1);
    s->set_awb_gain(s, 1);
    s->set_wb_mode(s, 0);   // 0 = Auto

    // --- Correcciones del sensor (clave para nitidez en OV3660) ---
    s->set_lenc(s, 1);       // lens correction (distorsión radial)
    s->set_bpc(s, 1);        // black pixel correction
    s->set_wpc(s, 1);        // white pixel correction
    s->set_raw_gma(s, 1);    // gamma correction
  }

  Serial.println("[CAM] OK");
  return true;
}

// ============================================================================
// WiFi
// ============================================================================
bool conectarWiFi() {
  Serial.printf("[WiFi] Conectando a SSID=%s\n", WIFI_SSID);
  ledAzul();

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long inicio = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - inicio < 30000UL) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("[WiFi] Conectado. IP=%s  RSSI=%d dBm\n",
                  WiFi.localIP().toString().c_str(), WiFi.RSSI());
    return true;
  }

  Serial.println("[WiFi] FALLÓ la conexión");
  ledAmarillo();
  return false;
}

bool asegurarWiFi() {
  if (WiFi.status() == WL_CONNECTED) return true;
  Serial.println("[WiFi] Desconectado, reconectando...");
  return conectarWiFi();
}

// ============================================================================
// NTP — sincroniza hora para timestamps ISO 8601
// ============================================================================
bool sincronizarHora() {
  Serial.println("[NTP] Sincronizando hora...");
  configTime(NTP_OFFSET_SEGUNDOS, NTP_DST_OFFSET, NTP_SERVER_1, NTP_SERVER_2);

  struct tm timeinfo;
  unsigned long inicio = millis();
  while (!getLocalTime(&timeinfo, 1000) && millis() - inicio < 15000UL) {
    Serial.print(".");
    delay(500);
  }
  Serial.println();

  if (!getLocalTime(&timeinfo)) {
    Serial.println("[NTP] FALLÓ");
    return false;
  }

  char buf[32];
  strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", &timeinfo);
  Serial.printf("[NTP] Hora local: %s\n", buf);
  return true;
}

// Devuelve timestamp ISO 8601 con offset Perú: "2026-05-23T14:32:11-05:00"
String timestampISO() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    return String("1970-01-01T00:00:00-05:00");
  }
  char buf[32];
  strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%S-05:00", &timeinfo);
  return String(buf);
}

// ============================================================================
// Request ID — UUID-like (MAC + millis + random) para idempotencia del POS
// ============================================================================
String generarRequestId() {
  uint64_t chip = ESP.getEfuseMac();
  char buf[40];
  snprintf(buf, sizeof(buf), "%08X-%08X-%lu-%04X",
           (uint32_t)(chip >> 32),
           (uint32_t)chip,
           millis(),
           (uint16_t)random(0xFFFF));
  return String(buf);
}

// ============================================================================
// Servidor HTTP local — stream en vivo para enfocar / inspeccionar sin reflashear
// Corre en su propia task (gestionada por esp_http_server). El loop principal
// sigue haciendo capturas cada 5 minutos en paralelo. La cámara es accedida
// por ambos vía esp_camera_fb_get() — el driver maneja la concurrencia con
// el fb_count=2 + CAMERA_GRAB_LATEST.
// ============================================================================
httpd_handle_t servidor_stream = NULL;

static const char* MJPEG_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=frame";
static const char* MJPEG_BOUNDARY     = "\r\n--frame\r\n";
static const char* MJPEG_PART_HEADER  = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

static const char INDEX_HTML[] PROGMEM = R"HTML(
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>ESP32-CAM — Stream en vivo</title>
<style>
  body { margin:0; background:#111; color:#eee; font-family:system-ui,sans-serif; text-align:center; }
  h1 { font-size:18px; margin:8px 0; font-weight:500; }
  p  { font-size:13px; margin:4px 0; opacity:.75; }
  img { max-width:100%; height:auto; display:block; margin:0 auto; border:1px solid #333; }
</style>
</head>
<body>
<h1>ESP32-CAM — Stream en vivo (XGA 1024x768)</h1>
<p>Esta es exactamente la imagen que se envia al backend cada 5 min. Ajustá enfoque/encuadre aqui.</p>
<img src="/stream" alt="stream">
</body>
</html>
)HTML";

static esp_err_t index_handler(httpd_req_t *req) {
  httpd_resp_set_type(req, "text/html");
  return httpd_resp_send(req, INDEX_HTML, strlen(INDEX_HTML));
}

static esp_err_t stream_handler(httpd_req_t *req) {
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
    // En UXGA con calidad 10, cada frame pesa ~200KB → el stream va a ~2-3 fps
    // sobre WiFi domestica. Suficiente para enfocar y verificar el encuadre.
    delay(100);
  }
  return res;
}

void iniciarServidorStream() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;
  config.stack_size  = 8192;

  httpd_uri_t uri_index  = { .uri = "/",       .method = HTTP_GET, .handler = index_handler,  .user_ctx = NULL };
  httpd_uri_t uri_stream = { .uri = "/stream", .method = HTTP_GET, .handler = stream_handler, .user_ctx = NULL };

  if (httpd_start(&servidor_stream, &config) == ESP_OK) {
    httpd_register_uri_handler(servidor_stream, &uri_index);
    httpd_register_uri_handler(servidor_stream, &uri_stream);
    Serial.println("[HTTP] Servidor de stream en puerto 80 listo");
  } else {
    Serial.println("[HTTP] No se pudo iniciar el servidor de stream");
  }
}

void iniciarMDNS() {
  if (MDNS.begin(HOSTNAME_MDNS)) {
    MDNS.addService("http", "tcp", 80);
    Serial.printf("[mDNS] Hostname registrado: http://%s.local/\n", HOSTNAME_MDNS);
  } else {
    Serial.println("[mDNS] No se pudo registrar el hostname (usar la IP directamente)");
  }
}

// ============================================================================
// Envío HTTP multipart al backend Python
// ============================================================================
bool enviarCaptura(camera_fb_t *fb) {
  if (!fb || fb->len == 0) {
    Serial.println("[HTTP] Frame buffer vacío");
    return false;
  }

  const char* boundary = "----ESP32CamBoundary7zXp";
  String preamble =
      String("--") + boundary + "\r\n" +
      "Content-Disposition: form-data; name=\"imagen\"; filename=\"captura.jpg\"\r\n" +
      "Content-Type: image/jpeg\r\n\r\n";
  String footer = String("\r\n--") + boundary + "--\r\n";

  size_t total = preamble.length() + fb->len + footer.length();

  // Reservar en PSRAM (8MB disponibles, JPEG SVGA ~50-100KB)
  uint8_t *body = (uint8_t*) ps_malloc(total);
  if (!body) {
    Serial.println("[HTTP] ps_malloc falló");
    return false;
  }

  memcpy(body, preamble.c_str(), preamble.length());
  memcpy(body + preamble.length(), fb->buf, fb->len);
  memcpy(body + preamble.length() + fb->len, footer.c_str(), footer.length());

  String url = String("http://") + BACKEND_HOST + ":" + BACKEND_PORT + "/api/v1/auditoria/captura";
  String ts = timestampISO();
  String reqId = generarRequestId();

  Serial.printf("[HTTP] POST %s  (%u bytes JPEG)\n", url.c_str(), (unsigned)fb->len);
  Serial.printf("[HTTP]   X-Request-Id: %s\n", reqId.c_str());

  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);
  http.begin(url);
  http.addHeader("Content-Type", String("multipart/form-data; boundary=") + boundary);
  http.addHeader("Authorization", String("Bearer ") + BACKEND_TOKEN);
  http.addHeader("X-Nodo-Id", NODO_ID);
  http.addHeader("X-Timestamp", ts);
  http.addHeader("X-Tipo-Evento", TIPO_EVENTO_DEFAULT);
  http.addHeader("X-Request-Id", reqId);

  int code = http.POST(body, total);
  free(body);

  bool ok = false;
  if (code > 0) {
    String resp = http.getString();
    Serial.printf("[HTTP] Status=%d  Body=%s\n", code, resp.c_str());
    ok = (code >= 200 && code < 300);
  } else {
    Serial.printf("[HTTP] Falló: %s\n", http.errorToString(code).c_str());
  }
  http.end();
  return ok;
}

bool enviarCapturaConReintentos(camera_fb_t *fb) {
  for (int intento = 1; intento <= HTTP_REINTENTOS_MAX; intento++) {
    if (!asegurarWiFi()) {
      Serial.println("[HTTP] Sin WiFi, no se puede enviar");
      return false;
    }
    Serial.printf("[HTTP] Intento %d/%d\n", intento, HTTP_REINTENTOS_MAX);
    if (enviarCaptura(fb)) return true;
    if (intento < HTTP_REINTENTOS_MAX) {
      unsigned long backoff = HTTP_BACKOFF_BASE_MS * (1UL << (intento - 1));  // 2s, 4s, 8s
      Serial.printf("[HTTP] Reintento en %lu ms\n", backoff);
      delay(backoff);
    }
  }
  return false;
}

// ============================================================================
// Ciclo principal: capturar + enviar
// ============================================================================
void capturaYEnvio() {
  Serial.println("\n========== Nueva captura ==========");

  // Warm-up: descartar 3 frames con un pequeño delay para que AEC/AGC/AWB
  // converjan tras 5 minutos sin capturar. La 4ta captura es la que se envía.
  for (int i = 0; i < 3; i++) {
    camera_fb_t *fb_warmup = esp_camera_fb_get();
    if (fb_warmup) esp_camera_fb_return(fb_warmup);
    delay(100);
  }

  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("[CAM] esp_camera_fb_get devolvió NULL");
    ledRojo();
    return;
  }

  bool ok = enviarCapturaConReintentos(fb);
  esp_camera_fb_return(fb);

  if (ok) {
    ledVerde();
    Serial.println("[OK] Captura enviada y aceptada por el backend");
  } else {
    ledRojo();
    Serial.println("[ERR] No se pudo enviar la captura");
  }
}

// ============================================================================
// SETUP
// ============================================================================
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n\n=== Firmware Auditoría Visual — ESP32-S3-CAM ===");

  led.begin();
  led.setBrightness(255);  // el LED_BRILLO ya escala los colores
  ledApagado();

  if (!inicializarCamara()) {
    ledRojo();
    Serial.println("[FATAL] Cámara no inicializa, reiniciando en 10s");
    delay(10000);
    ESP.restart();
  }

  if (!conectarWiFi()) {
    ledAmarillo();
    Serial.println("[FATAL] WiFi no conecta, reiniciando en 10s");
    delay(10000);
    ESP.restart();
  }

  if (!sincronizarHora()) {
    Serial.println("[WARN] NTP falló — timestamps serán 1970, continuamos");
  }

  iniciarMDNS();
  iniciarServidorStream();

  Serial.println();
  Serial.println("==========================================================");
  Serial.printf("  Stream en vivo:  http://%s.local/   (recomendado)\n", HOSTNAME_MDNS);
  Serial.printf("                   http://%s/\n", WiFi.localIP().toString().c_str());
  Serial.println("  Usalo para enfocar/inspeccionar sin reflashear.");
  Serial.println("==========================================================");

  randomSeed(esp_random());

  // Captura inmediata al arrancar (no esperar 5 min la primera vez)
  capturaYEnvio();
}

// ============================================================================
// LOOP
// ============================================================================
void loop() {
  static unsigned long ultimaCaptura = millis();

  if (millis() - ultimaCaptura >= INTERVALO_CAPTURA_MS) {
    capturaYEnvio();
    ultimaCaptura = millis();
  }

  // Mantener WiFi vivo
  if (WiFi.status() != WL_CONNECTED) {
    ledAmarillo();
    conectarWiFi();
  }

  delay(1000);
}
```

---

## Notas técnicas del código

### Memoria
- JPEG UXGA pesa **~150-250 KB**. El body multipart total ~250 KB.
- Se reserva en **PSRAM** con `ps_malloc()` para no agotar el heap normal (~250 KB libres).
- La placa tiene **8 MB de PSRAM**, sobra muchísimo.

### Timestamp
- Formato ISO 8601 con offset Perú: `2026-05-23T14:32:11-05:00`.
- El backend Python lo parsea con `datetime` (FastAPI lo convierte automáticamente).
- Si NTP falla, manda `1970-01-01T00:00:00-05:00` y el backend lo aceptará pero el POS rechazará si está configurado como required (después de aplicar `POS_AJUSTES_PENDIENTES.md` #2).

### Request ID
- Formato: `<MAC_high>-<MAC_low>-<millis>-<random16>`. Ejemplo: `14C19FC1-B7600000-12345-ABCD`.
- Único por captura → el POS lo usa para idempotencia (después del ajuste #1).

### LED RGB
- **Azul**: conectando WiFi/NTP
- **Verde**: captura enviada y aceptada (200/201)
- **Amarillo**: sin WiFi
- **Rojo**: error de cámara o backend rechazó (4xx/5xx) o timeout

### Reintentos
- 3 intentos con backoff exponencial: 2s → 4s → 8s.
- Si los 3 fallan, espera al siguiente ciclo (5 min) sin dropear nada — el firmware no buffea capturas perdidas.

### Resolución y costos
- UXGA 1600x1200 a calidad JPEG 10 da ~200 KB por foto.
- Claude Sonnet 4.6 cobra por tokens visuales. UXGA ≈ 3500 tokens visuales aprox. = $0.012 por foto (aprox).
- Con captura cada 5 min: 288 fotos/día = ~$3.50/día. Para demo y MVP, aceptable.
- Si hace falta bajar costo: SXGA (1280x1024) ≈ $0.008/foto = ~$2.30/día.
- Si hace falta bajar más: XGA (1024x768) ≈ $0.005/foto = ~$1.40/día.

### Foco del lente (OV3660)
- El OV3660 **NO tiene autofocus** (eso es del OV5640). El aro plástico del lente
  se gira a mano para enfocar a la distancia de trabajo (típicamente 30-50 cm
  del estante).
- Para enfocar con feedback en vivo, flashear primero el sketch de
  `FIRMWARE_ENFOQUE.md` y abrir `http://<ip-esp32>/` en Chrome.
- Una vez enfocado, **no tocar más el aro** — el firmware de auditoría se queda
  con ese foco físico.

### Sensor settings y warm-up
- El bloque de `inicializarCamara()` aplica sharpness=2, denoise=1, lens
  correction y AEC/AGC/AWB en modo auto. Esto compensa la suavidad inherente
  del lente plástico y se adapta automáticamente a la iluminación del estante.
- Se descartan **3 frames** antes de cada captura para que AEC/AWB converjan
  tras 5 minutos sin actividad. Esto agrega ~400 ms al ciclo de captura.

### Stream en vivo + mDNS
- El firmware levanta un servidor HTTP en el puerto 80 con dos endpoints:
  - `GET /`       → HTML con `<img src="/stream">`
  - `GET /stream` → MJPEG continuo a ~2-3 fps (UXGA es pesado)
- Se accede desde cualquier dispositivo en la misma WiFi:
  - `http://esp32-cam.local/` (mDNS, recomendado — funciona si tu PC tiene
    Bonjour/Avahi; viene con iTunes en Windows, nativo en macOS/Linux)
  - `http://<ip-del-esp32>/` (fallback — la IP la imprime al Serial al arrancar)
- El stream y la captura periódica de 5 min usan la misma cámara. El driver
  maneja la concurrencia con `fb_count=2` + `CAMERA_GRAB_LATEST` — si una
  captura periódica cae mientras hay stream activo, simplemente toma el último
  frame del buffer; el stream sigue, solo se nota un microhipo de 1 frame.
- Mientras estés en el stream el LED puede parpadear normal (verde/rojo/azul)
  porque la captura periódica sigue mandando al backend en paralelo.