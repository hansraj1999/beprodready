# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser

FROM base AS deps
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM base AS runtime
COPY --from=deps --chown=appuser:appuser /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

COPY alembic.ini .
COPY alembic ./alembic
COPY scripts ./scripts
COPY app ./app
# Strip CRLF if the build context came from Windows (fixes "no such file or directory" on exec).
RUN sed -i 's/\r$//' /app/scripts/docker-entrypoint.sh
RUN chown -R appuser:appuser /app \
    && chmod +x /app/scripts/docker-entrypoint.sh

USER appuser

EXPOSE 8000

# Use /bin/sh explicitly so CRLF in the file (Windows checkouts) cannot break the shebang.
ENTRYPOINT ["/bin/sh", "/app/scripts/docker-entrypoint.sh"]
