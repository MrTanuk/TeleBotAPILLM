# ==========================================
# STAGE 1: Builder (Install dependencies)
# ==========================================
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install tools for compiling (Will be discarded later)
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential git

WORKDIR /app

# Install dependencies using uv
COPY pyproject.toml uv.lock ./
# Sync dependencies into a virtual environment (.venv)
RUN uv sync --frozen --no-dev

# ==========================================
# STAGE 2: Runner (Lightweight Final Image)
# ==========================================
FROM python:3.12-slim

# Install ONLY runtime dependencies (FFmpeg is vital for audio/video)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the virtual environment from the 'builder' stage
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY src/ ./src/

# Configure the PATH to use the virtual environment automatically
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

# Execute
CMD uvicorn src.botgram_py.main:app --host 0.0.0.0 --port ${PORT:-8080}
