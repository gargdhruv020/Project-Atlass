#!/bin/bash
set -e

echo "=================================================================="
echo " Project Atlas - FastAPI Backend Starting in Docker"
echo "=================================================================="

# Wait for MySQL to become ready
echo "[Entrypoint] Verifying MySQL connection at ${DB_HOST}:${DB_PORT}..."
python - << 'EOF'
import os
import sys
import time
import pymysql

host = os.environ.get("DB_HOST", "mysql")
port = int(os.environ.get("DB_PORT", 3306))
user = os.environ.get("DB_USER", "root")
password = os.environ.get("DB_PASSWORD", "258000")
database = os.environ.get("DB_NAME", "project_atlas")

max_retries = 30
retry_interval = 2

for attempt in range(1, max_retries + 1):
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            connect_timeout=3
        )
        conn.close()
        print(f"[Entrypoint] Successfully connected to MySQL at {host}:{port}/{database}")
        sys.exit(0)
    except Exception as e:
        if attempt < max_retries:
            print(f"[Entrypoint] Waiting for MySQL ({attempt}/{max_retries})... ({e})")
            time.sleep(retry_interval)
        else:
            print(f"[Entrypoint] ERROR: Could not connect to MySQL after {max_retries} attempts.")
            sys.exit(1)
EOF

# Idempotent Ingestion Check
if [ "${AUTO_INGEST_ON_STARTUP:-true}" = "true" ]; then
    echo "[Entrypoint] Running startup vector ingestion check..."
    python /app/backend/scripts/startup_ingest.py
fi

# Start FastAPI application
echo "[Entrypoint] Starting FastAPI server on port 8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
