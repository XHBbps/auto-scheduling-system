FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml requirements.lock ./
COPY app ./app

RUN pip install --upgrade pip && pip install -r requirements.lock

COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts ./scripts
COPY docker ./docker

RUN chmod +x /app/docker/backend-entrypoint.sh /app/docker/worker-entrypoint.sh /app/docker/scheduler-entrypoint.sh

EXPOSE 8000

RUN useradd -r -s /usr/sbin/nologin -u 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

CMD ["/app/docker/backend-entrypoint.sh"]
