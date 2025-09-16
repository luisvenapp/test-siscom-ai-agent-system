# --- Builder Stage ---
FROM python:3.10.12-slim as builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

RUN apt-get update -qq && \
    apt-get install --no-install-recommends --yes \
    build-essential libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix="/install" -r requirements.txt

# --- Final Stage ---
FROM python:3.10.12-slim

WORKDIR /app

RUN addgroup --system app && \
    adduser --system --ingroup app app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/app/.local/bin:${PATH}" \
    TRANSFORMERS_CACHE=/home/app/.cache/huggingface/hub \
    PYTHONPATH=/app/backend \
    MPLCONFIGDIR=/tmp \
    HOME=/home/app

# Instalar runtime deps + soporte de certificados
RUN apt-get update -qq && \
    apt-get install --no-install-recommends --yes libpq-dev curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# 🔑 Copiar CA corporativa y actualizar trust store
COPY certs/ca.crt /usr/local/share/ca-certificates/ca.crt
RUN update-ca-certificates

# Copiar dependencias Python
COPY --from=builder /install /usr/local

# Copiar app
COPY . .
RUN chmod +x /app/entrypoint.sh

RUN mkdir -p /home/app/.cache/huggingface && \
    chown -R app:app /app /home/app

USER app

EXPOSE 8001

ENTRYPOINT ["/app/entrypoint.sh"]
