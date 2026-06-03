# Railway root Dockerfile
# Railway asigna puerto automáticamente via variable $PORT.
# Uvicorn DEBE escuchar en ese puerto para que Railway enrute el tráfico.

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Compilar extensiones C de uvicorn[standard]
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend_vision/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend_vision/src/ ./src/

# Railway inyecta $PORT automáticamente (ej. 8080).
# Usamos shell-form para que sh expanda la variable.
# Si Railway no inyecta $PORT, fallback a 8000.
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
