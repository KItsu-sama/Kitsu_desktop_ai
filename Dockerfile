# Dockerfile
# Minimal Python runtime for Kitsu Desktop AI on Hugging Face Spaces.
# llama-cpp-python removed — HF Space runs as a lightweight gateway only
# (--serve --safe). Inference is handled by an external endpoint via LLM_BASE_URL.

FROM python:3.10-slim

# No C++ toolchain needed anymore — all deps are pure-Python wheels.
# curl is kept for health-check probes in HF's container orchestrator.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user with UID 1000 for Spaces compatibility
RUN groupadd -g 1000 kitsu && useradd --no-log-init -u 1000 -g kitsu kitsu

WORKDIR /app

# Install runtime dependencies before copying source (layer cache friendly)
COPY requirements.txt pyproject.toml /app/
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY . /app
RUN mkdir -p /app/data /app/data/runtime /app/data/logs \
    && chown -R kitsu:kitsu /app /app/data /app/data/runtime /app/data/logs

USER kitsu
ENV HOME=/home/kitsu
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV KITSU_SAFE_MODE=1
ENV KITSU_STRIP_DESKTOP_PLUGINS=1
# LLM_BASE_URL: point to your local Ollama or any OpenAI-compat endpoint.
# Leave empty to run in gateway-only mode (no inference).
ENV LLM_BASE_URL=""
ENV LLM_MODEL="tinyllama:1.1b"

EXPOSE 7860
CMD ["python", "r.py", "--safe", "--serve", "--port", "7860"]