# ==========================================
# STAGE 1: Builder (Temporary, we compile everything here)
# ==========================================
FROM python:3.12-slim AS builder

# 1. Install tools for compiling (Will be discarded later)
RUN apt-get update && \
  apt-get install -y --no-install-recommends build-essential git neovim

# 2. Install Poetry
RUN pip install "poetry==2.0.1"

# 3. Configure Poetry to create the venv INSIDE the project
ENV POETRY_NO_INTERACTION=1 \
  POETRY_VIRTUALENVS_IN_PROJECT=1 \
  POETRY_VIRTUALENVS_CREATE=1

WORKDIR /app

# 4. Install dependencies
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --only main

# ==========================================
# STAGE 2: Runner (Lightweight Final Image)
# ==========================================
FROM python:3.12-slim

# 1. Install ONLY runtime dependencies (FFmpeg is vital for audio/video)
# We delete apt lists at the end to save space
RUN apt-get update && \
  apt-get install -y --no-install-recommends ffmpeg && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Copy the virtual environment from the 'builder' stage
# This is what saves space: we don't bring poetry, gcc, or git.
COPY --from=builder /app/.venv /app/.venv

# 3. Copy source code
COPY src/ ./src/

# 4. Configure the PATH to use the virtual environment automatically
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

# 5. Execute
CMD uvicorn src.telegram_bot.main:app --host 0.0.0.0 --port ${PORT:-8080}
