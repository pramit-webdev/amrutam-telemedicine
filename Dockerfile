FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml .
RUN uv sync --no-dev --frozen

FROM python:3.12-slim

RUN groupadd -r amrutam && useradd -r -g amrutam amrutam

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY app/ app/
COPY alembic.ini alembic/ alembic/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app

EXPOSE 8000

USER amrutam
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
