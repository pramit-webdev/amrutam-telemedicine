#!/bin/bash
set -e

alembic upgrade head 2>/dev/null || alembic stamp head

exec uvicorn app.main:app --host 0.0.0.0 --port 10000
