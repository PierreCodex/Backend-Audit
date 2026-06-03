r"""
Ver el conteo de Claude sobre una imagen, sin ESP32 ni POS.

Uso (desde backend_vision/, con el venv):
    .\.venv\Scripts\python.exe ver_conteo.py
        -> usa la captura mas reciente de storage/debug/

    .\.venv\Scripts\python.exe ver_conteo.py ruta\a\la\imagen.jpg
        -> usa la imagen que le pases

Imprime: cada producto detectado (nombre, cantidad, confianza), el total,
la confianza general, si hay espacios vacios y las observaciones de Claude.
"""
import asyncio
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from anthropic import AsyncAnthropic  # noqa: E402

from infrastructure.ia.claude_analizador import ClaudeAnalizador  # noqa: E402
from shared.config import Settings  # noqa: E402


def elegir_imagen() -> str | None:
    if len(sys.argv) > 1:
        return sys.argv[1]
    candidatos = glob.glob(os.path.join("storage", "debug", "*.jpg"))
    if not candidatos:
        return None
    return max(candidatos, key=os.path.getmtime)  # la mas reciente


async def main() -> None:
    ruta = elegir_imagen()
    if not ruta or not os.path.isfile(ruta):
        print("No encontre ninguna imagen. Pasa una ruta o pon capturas en storage/debug/.")
        return

    settings = Settings()  # lee .env (ANTHROPIC_API_KEY, CLAUDE_MODEL)
    with open(ruta, "rb") as f:
        imagen = f.read()

    print(f"Imagen analizada : {ruta}  ({len(imagen) // 1024} KB)")
    print(f"Modelo           : {settings.claude_model}")
    print("Llamando a Claude...\n")

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    analizador = ClaudeAnalizador(client, settings.claude_model)
    a = await analizador.analizar(imagen)

    print("=" * 56)
    print("  CONTEO DE CLAUDE")
    print("=" * 56)
    if a.detecciones:
        for d in a.detecciones:
            print(f"  - {d.nombre:<32} x{d.cantidad:<3}  (conf {d.confianza.valor:.0%})")
    else:
        print("  (Claude no detecto productos)")
    print("-" * 56)
    print(f"  Cantidad total   : {a.cantidad_total}")
    print(f"  Confianza general: {a.confianza_general.valor:.0%}")
    print(f"  Espacios vacios  : {'si' if a.espacios_vacios else 'no'}")
    if a.observaciones:
        print(f"  Observaciones    : {a.observaciones}")
    print("=" * 56)


if __name__ == "__main__":
    asyncio.run(main())