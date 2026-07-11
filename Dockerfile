FROM python:3.12-slim

RUN groupadd -r amrutam && useradd -r -g amrutam amrutam && \
    apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY alembic.ini .
COPY alembic/ alembic/

ENV PYTHONPATH=/app

USER amrutam

EXPOSE 8000

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
