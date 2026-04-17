# =============================================================================
# NyayaSetu Backend - Production Dockerfile
#
# Matches your localhost environment byte-for-byte:
#   - Python 3.11 (same as local)
#   - Exact pinned versions from requirements.txt
#   - FAISS index + sentence-transformer model bundled in (no download at boot)
#   - Starts uvicorn on $PORT (Render provides this automatically)
# =============================================================================

FROM python:3.11-slim

# System deps:
#   - libgomp1: required by faiss-cpu
#   - build-essential: only for packages that lack a wheel (cleaned up after pip)
#   - ca-certificates: TLS for Groq/Sarvam API calls
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgomp1 \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Python dependencies ---------------------------------------------------
# Install CPU-only torch FIRST to avoid pulling 5GB of NVIDIA CUDA packages.
# sentence-transformers will then reuse this torch wheel instead of fetching
# the default (CUDA) one from PyPI.
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --index-url https://download.pytorch.org/whl/cpu \
        torch==2.8.0 torchvision==0.23.0 \
    && pip install -r requirements.txt

# --- Application code ------------------------------------------------------
COPY src/ ./src/

# --- FAISS index and embedder model (bundled - no runtime download) --------
# Only the files production needs; audio cache, formatted_docs, governance.db excluded via .dockerignore
COPY data/schemes_faiss.index ./data/
COPY data/schemes_metadata.pkl ./data/
COPY data/schemes_seed.json ./data/
COPY models/ ./models/

# Create runtime writable dirs (audio cache, formatted docs)
RUN mkdir -p /app/data/audio /app/data/formatted_docs

# --- Non-root user (security) ----------------------------------------------
RUN groupadd -r nyaya && useradd -r -g nyaya nyaya \
    && chown -R nyaya:nyaya /app
USER nyaya

# --- Runtime ---------------------------------------------------------------
# Render sets $PORT. Fallback for local docker run.
ENV PORT=8001
EXPOSE 8001

# Healthcheck - backend exposes /health at root (no /api/v1 prefix)
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f "http://localhost:${PORT}/health" || exit 1

# Start FastAPI via uvicorn. `sh -c` needed so $PORT expands.
CMD ["sh", "-c", "uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT}"]
