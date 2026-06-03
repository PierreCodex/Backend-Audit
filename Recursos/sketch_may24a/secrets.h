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
//
// MODO NGROK (demo rápida): URL que te da ngrok, ej:
//   #define BACKEND_HOST  "abc123.ngrok-free.app"
//   #define BACKEND_PORT  80
//
// MODO RAILWAY (producción): URL pública del deploy, ej:
//   #define BACKEND_HOST  "mi-vision.up.railway.app"
//   #define BACKEND_PORT  443
//   ⚠️ Railway usa HTTPS. El firmware actual hace HTTP simple.
//      Para Railway se necesita modificar el .ino para WiFiClientSecure + setInsecure()
//      o usar un proxy HTTP. Consultar README del backend.
//
#define BACKEND_HOST   "192.168.1.9"
#define BACKEND_PORT   8000

// ============================================================================
// Token de auth del backend (debe coincidir con ESP32_API_TOKEN del .env / Railway)
// ============================================================================
// Token actual para producción/demo (generado el 2026-06-02):
#define BACKEND_TOKEN  "EA16BA4F423CDE9FD8A5A154EED7B1815A5B5EBC42762D816D6B4A3513A4D5C7"