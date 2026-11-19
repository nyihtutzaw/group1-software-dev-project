# Production image for Cloud Run: the API and the built frontend in one container.
# Build from the repo root:  docker build -f infra/cloudrun/Dockerfile .
# (Local development keeps using docker-compose.yml with backend/ and frontend/ Dockerfiles.)

# --- 1. Build the React app ------------------------------------------------------------------
FROM node:24-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- 2. API + static files -------------------------------------------------------------------
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /bin/

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-cache

COPY backend/ ./
COPY --from=web /web/dist /app/static

# Production defaults; secrets and DATABASE_URL come from Cloud Run (Secret Manager).
ENV APP_ENV=production \
    STATIC_DIR=/app/static \
    STORAGE_DIR=/data/evidence \
    FORWARDED_IP_HOPS=1 \
    PORT=8080

EXPOSE 8080
# No --reload; --proxy-headers so redirects use https (Cloud Run terminates TLS).
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*' --no-server-header"]
