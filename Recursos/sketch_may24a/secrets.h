#pragma once

// ============================================================================
// WiFi — usar el hotspot del celular para la demo (red controlada)
// ============================================================================
#define WIFI_SSID      "CORDOVA 2.4G"
#define WIFI_PASSWORD  "73MC8217"

// ============================================================================
// Backend Python
// ============================================================================
// MODO LOCAL (desarrollo): IP de tu laptop en la WiFi actual
//   Windows: ipconfig → "Adaptador de LAN inalámbrica Wi-Fi" → IPv4
//   macOS:   ipconfig getifaddr en0
//   Linux:   hostname -I
//   Ejemplo:
//     #define BACKEND_HOST  "192.168.1.9"
//     #define BACKEND_PORT  8000
//
// MODO RAILWAY (producción — para la demo con tu amigo):
//   Railway te da una URL pública tipo "mi-vision.up.railway.app"
//   El firmware detecta puerto 443 y usa WiFiClientSecure automáticamente.
//   Ejemplo:
//     #define BACKEND_HOST  "mi-vision.up.railway.app"
//     #define BACKEND_PORT  443
//
#define BACKEND_HOST   "192.168.1.9"
#define BACKEND_PORT   8000

// ============================================================================
// Token de auth del backend (debe coincidir con ESP32_API_TOKEN del .env / Railway)
// ============================================================================
// Token actual para producción/demo (generado el 2026-06-02):
#define BACKEND_TOKEN  "EA16BA4F423CDE9FD8A5A154EED7B1815A5B5EBC42762D816D6B4A3513A4D5C7"