# ══════════════════════════════════════════════════════════════════════════════
# DRIP API — Production Dockerfile
# ══════════════════════════════════════════════════════════════════════════════
# Multi-stage build:
#   Stage 1 (builder): Install dependencies in isolated layer
#   Stage 2 (runtime): Lean final image without build tools

# ── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

# Install system dependencies needed to compile some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libmagic1 \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy only requirements first (layer caching — only rebuilds on dep changes)
COPY requirements.txt .

# Install into a prefix directory for clean copy to runtime stage
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

# Create non-root user for security
RUN groupadd -r drip && useradd -r -g drip -d /app drip

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY --chown=drip:drip . .

# Switch to non-root user
USER drip

# Expose port
EXPOSE 8000

# Health check for container orchestrators
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# ── Production server command ─────────────────────────────────────────────────
# 2 workers per CPU core is a common starting point for I/O-bound FastAPI apps.
# Railway sets $PORT; fall back to 8000.
CMD uvicorn main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --workers 2 \
    --loop uvloop \
    --http httptools \
    --access-log \
    --no-use-colors \
    --timeout-keep-alive 30