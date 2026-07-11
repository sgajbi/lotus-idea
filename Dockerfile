ARG PYTHON_BASE_IMAGE=python:3.12-slim
FROM ${PYTHON_BASE_IMAGE}

ARG PYTHON_BASE_IMAGE
ARG GIT_COMMIT_SHA=unknown
ARG GIT_BRANCH=unknown
ARG BUILD_TIMESTAMP=unknown
ARG REPO_URL=unknown
ARG CI_RUN_ID=local
ARG IMAGE_BUILD_ID=local
ARG SERVICE_VERSION=0.1.0

LABEL org.opencontainers.image.title="lotus-idea" \
      org.opencontainers.image.description="Lotus opportunity intelligence domain service" \
      org.opencontainers.image.base.name="${PYTHON_BASE_IMAGE}" \
      org.opencontainers.image.version="${SERVICE_VERSION}" \
      org.opencontainers.image.revision="${GIT_COMMIT_SHA}" \
      io.lotus.image.git.branch="${GIT_BRANCH}" \
      org.opencontainers.image.created="${BUILD_TIMESTAMP}" \
      org.opencontainers.image.source="${REPO_URL}" \
      io.lotus.image.ci.run_id="${CI_RUN_ID}" \
      io.lotus.image.build.id="${IMAGE_BUILD_ID}" \
      io.lotus.image.identity.contract="lotus.image-identity.v1" \
      io.lotus.image.registry.digest.binding="runtime-release-manifest"

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    LOTUS_GIT_COMMIT_SHA="${GIT_COMMIT_SHA}" \
    LOTUS_GIT_BRANCH="${GIT_BRANCH}" \
    LOTUS_BUILD_TIMESTAMP="${BUILD_TIMESTAMP}" \
    LOTUS_REPO_URL="${REPO_URL}" \
    LOTUS_CI_RUN_ID="${CI_RUN_ID}" \
    LOTUS_IMAGE_BUILD_ID="${IMAGE_BUILD_ID}" \
    LOTUS_SERVICE_VERSION="${SERVICE_VERSION}"

WORKDIR /app

COPY pyproject.toml README.md ./
COPY requirements/runtime-resolved.lock.txt ./requirements/runtime-resolved.lock.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir --requirement requirements/runtime-resolved.lock.txt

COPY src ./src
RUN python -m pip install --no-cache-dir --no-deps .

COPY contracts ./contracts
COPY migrations ./migrations
COPY docs/examples/source-ingestion/canonical-high-cash-worker.manifest.json ./docs/examples/source-ingestion/canonical-high-cash-worker.manifest.json
COPY scripts/proof_generator_io.py ./scripts/proof_generator_io.py
COPY scripts/run_source_ingestion_worker.py ./scripts/run_source_ingestion_worker.py
COPY scripts/run_scheduled_source_ingestion_worker.py ./scripts/run_scheduled_source_ingestion_worker.py

RUN groupadd --system lotus \
    && useradd --system --gid lotus --home-dir /app --shell /usr/sbin/nologin lotus \
    && chown -R lotus:lotus /app

USER lotus

EXPOSE 8330
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8330"]
