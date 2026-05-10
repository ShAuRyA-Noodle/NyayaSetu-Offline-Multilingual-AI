# =============================================================================
# NyayaSetu Backend - Production Dockerfile (multi-stage)
#
# Targets:
#   - Hugging Face Spaces (Docker SDK, app_port=7860, persistent FS)
#   - Local docker-compose backend profile
#   - Any Docker-compatible host
#
# Behavior:
#   - Stage 1 (builder) compiles wheels with build deps, then is discarded.
#   - Stage 2 (runtime) is slim, non-root, no compilers shipped.
#   - $PORT is honored at runtime (8001 local, 7860 on HF Spaces).
#   - Model + FAISS index are NOT baked in. The rag_engine self-rebuilds the
#     index from the seed data on first boot if data/schemes_faiss.index is
#     missing. Sentence-transformer is downloaded on first boot to
#     $TRANSFORMERS_CACHE which is mounted on HF Spaces persistent storage.
# =============================================================================

# ------------------------- Stage 1: builder ----------------------------------
FROM python:3.11-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .

# CPU-only torch first (avoids 5GB CUDA pull). sentence-transformers reuses it.
RUN pip install --upgrade pip \
    && pip wheel --wheel-dir /wheels \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        torch==2.8.0 torchvision==0.23.0 \
    && pip wheel --wheel-dir /wheels -r requirements.txt


# ------------------------- Stage 2: runtime ----------------------------------
FROM python:3.11-slim AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TRANSFORMERS_CACHE=/app/models \
    HF_HOME=/app/models \
    SENTENCE_TRANSFORMERS_HOME=/app/models \
    PORT=8001

# Runtime-only system deps.
#   - libgomp1: required by faiss-cpu
#   - ca-certificates: TLS for Groq / Sarvam API calls
# (curl removed; healthcheck uses pure Python now)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgomp1 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install pre-built wheels from the builder stage.
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-index --find-links=/wheels \
        torch==2.8.0 torchvision==0.23.0 \
    && pip install --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# Application code only. Index/model are built / fetched at runtime.
COPY src/ ./src/
COPY data/schemes_seed.json ./data/

# Writable runtime dirs (audio cache, formatted docs, model cache, FAISS index).
RUN mkdir -p /app/data/audio /app/data/formatted_docs /app/models

# Non-root user (HF Spaces also expects uid 1000).
RUN useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

# HF Spaces requires 7860; local default 8001. EXPOSE both for clarity.
EXPOSE 7860 8001

# Healthcheck without curl — pure Python urllib.
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import os, urllib.request, sys; \
url='http://localhost:'+os.environ.get('PORT','8001')+'/health'; \
sys.exit(0 if urllib.request.urlopen(url, timeout=5).status==200 else 1)" || exit 1

# Start FastAPI via uvicorn. `sh -c` so $PORT expands.
CMD ["sh", "-c", "uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT}"]
