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