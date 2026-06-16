# syntax=docker/dockerfile:1.7

# ==========================
# Builder
# ==========================
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /build

RUN python -m venv /opt/venv

COPY requirements.txt .

RUN /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# ==========================
# Runtime
# ==========================
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV PATH="/opt/venv/bin:$PATH"

# Runtime configuration
ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000
ENV AUTH_TOKEN=local-dev-token
ENV SERVICE_NAME=iot-ingestion
ENV SERVICE_VERSION=0.5.0

WORKDIR /app

# Create non-root user
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup --home /app appuser

# Copy virtualenv
COPY --from=builder /opt/venv /opt/venv

# Copy application
COPY src/ ./src/

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s \
            --timeout=5s \
            --start-period=10s \
            --retries=3 \
CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()" || exit 1

# Start FastAPI
CMD ["sh","-c","uvicorn iot_app.main:app --app-dir src --host ${APP_HOST} --port ${APP_PORT}"]