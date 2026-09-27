FROM python:3.13-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY pyproject.toml ./
COPY core core
COPY ingest ingest
COPY retrieval retrieval
COPY generation generation
COPY eval eval
COPY api api
RUN pip install --no-cache-dir .

# Hosts (Railway, Render, Fly) inject PORT; locally it defaults to 8000.
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
