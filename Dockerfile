ARG PYTHON_BASE_IMAGE=python:3.12-slim
FROM ${PYTHON_BASE_IMAGE}

ARG PYTHON_BASE_IMAGE

LABEL org.opencontainers.image.title="lotus-idea" \
      org.opencontainers.image.description="Lotus opportunity intelligence domain service" \
      org.opencontainers.image.base.name="${PYTHON_BASE_IMAGE}"

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY pyproject.toml README.md ./
COPY requirements/runtime-resolved.lock.txt ./requirements/runtime-resolved.lock.txt
COPY src ./src
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir --constraint requirements/runtime-resolved.lock.txt .

COPY contracts ./contracts
COPY migrations ./migrations
COPY scripts/run_source_ingestion_worker.py ./scripts/run_source_ingestion_worker.py
COPY scripts/run_scheduled_source_ingestion_worker.py ./scripts/run_scheduled_source_ingestion_worker.py

RUN groupadd --system lotus \
    && useradd --system --gid lotus --home-dir /app --shell /usr/sbin/nologin lotus \
    && chown -R lotus:lotus /app

USER lotus

EXPOSE 8330
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8330"]
