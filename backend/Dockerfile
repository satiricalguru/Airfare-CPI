FROM python:3.12-slim

# Don't buffer stdout/stderr, don't write .pyc files.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Build dependencies for compiled wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies first so the layer caches independently of app code.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run as an unprivileged user. Previously this image ran as root, so a container
# escape or a code-execution bug would have had root in the container.
RUN useradd --create-home --shell /usr/sbin/nologin --uid 10001 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Surface readiness to Docker/compose instead of assuming the process is healthy.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
