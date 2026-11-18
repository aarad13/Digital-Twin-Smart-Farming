#!/bin/sh
set -eu
cd /app

echo "Waiting for MySQL..."
python scripts/wait_for_mysql.py

echo "Initializing database schema..."
python scripts/init_db.py

echo "Applying account and organisation-access migrations..."
python scripts/migrate_app_access.py

echo "Importing bundled experimental observations (idempotent)..."
python scripts/import_dataset.py

echo "Running project integrity and application/database checks..."
python scripts/check_project.py --with-db

echo "Starting Flask application..."
exec python run.py
