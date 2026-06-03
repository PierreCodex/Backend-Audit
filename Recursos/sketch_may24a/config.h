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
// ~2.5x más nítido que SVGA pero liviano. UXGA (1600x1200, 226 KB) saturaba el
// módulo: el envío HTTP se cortaba ("send payload failed") y la cámara
// desbordaba el buffer DMA ("cam_hal: FB-OVF"), por consumo de memoria y ancho
// de banda de PSRAM con WiFi + stream a la vez. Si XGA va estable y querés más
// nitidez, subir de a un paso: XGA → SXGA (1280x1024) → UXGA, validando cada uno.
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

// Captura manual bajo demanda: cada cuánto el ESP32 le pregunta al backend si la
// interfaz web pidió una captura (GET /api/v1/capturas/pendiente). Más bajo = el botón
// "Capturar ahora" responde más rápido, pero son más requests. 4s es buen balance.
#define POLL_PENDIENTE_MS     4000

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