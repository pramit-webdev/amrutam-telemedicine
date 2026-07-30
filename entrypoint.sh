#!/bin/bash
set -e

alembic stamp 5c95691ca0d1 2>/dev/null || true
alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port 10000
