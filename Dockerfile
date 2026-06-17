# Build a minimal Python runtime for Kitsu Desktop AI on Hugging Face Spaces.
# The container runs as non-root and exposes a lightweight HTTP health service.

FROM python:3.10-slim


# Install system libraries required by llama-cpp-python wheel (OpenBLAS)
RUN apt-get update && apt-get install -y \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user with UID 1000 for Spaces compatibility
RUN groupadd -g 1000 kitsu && useradd --no-log-init -u 1000 -g kitsu kitsu

WORKDIR /app

# Install runtime dependencies first, then copy application.
COPY requirements.txt pyproject.toml /app/
RUN python -m pip install --upgrade pip setuptools wheel
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . /app
RUN mkdir -p /app/data /app/data/runtime /app/data/logs && \
    chown -R kitsu:kitsu /app /app/data /app/data/runtime /app/data/logs

USER kitsu
ENV HOME=/home/kitsu
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV KITSU_SAFE_MODE=1
ENV KITSU_STRIP_DESKTOP_PLUGINS=1

EXPOSE 7860
CMD ["python", "r.py", "--serve", "--port", "7860"]
