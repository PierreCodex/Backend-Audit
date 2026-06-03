# Railway root Dockerfile
# Railway detecta puerto automáticamente. Usamos 8000 como default.

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000 \
    PYTHONPATH=/app/src

WORKDIR /app

# Instalar gcc para compilar extensiones C de uvicorn[standard]
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend_vision/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend_vision/src/ ./src/

# Railway espera que la app escuche en el puerto definido por $PORT.
# Como definimos ENV PORT=8000, uvicorn escucha ahí.
# Railway redirige el tráfico público a ese puerto interno.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
