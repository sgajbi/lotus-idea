FROM python:3.12-slim

ENV PIP_ROOT_USER_ACTION=ignore

WORKDIR /app
COPY pyproject.toml README.md ./
COPY contracts ./contracts
COPY migrations ./migrations
COPY src ./src
COPY scripts ./scripts
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -e ".[dev]"

EXPOSE 8330
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8330"]
