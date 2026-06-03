# Railway root Dockerfile
# Este Dockerfile está en la raíz del repo porque Railway construye desde aquí.
# La versión en backend_vision/Dockerfile es para desarrollo local.

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Instalar gcc y herramientas de build para paquetes con extensiones C (uvloop, httptools, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend_vision/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend_vision/src/ ./src/

ENV PYTHONPATH=/app/src

EXPOSE 8000

# Usar $PORT (Railway lo inyecta automáticamente, default 8000 para compatibilidad local)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
