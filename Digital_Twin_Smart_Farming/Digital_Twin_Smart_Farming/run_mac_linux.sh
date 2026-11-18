#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  echo "Run ./setup_mac_linux.sh first (or use Docker: docker compose up --build)." >&2
  exit 1
fi
source .venv/bin/activate
if [[ ! -f .env ]]; then cp .env.example .env; fi
USE_DOCKER_MYSQL="$(python -c "from dotenv import dotenv_values; print(dotenv_values('.env').get('USE_DOCKER_MYSQL', '1'))")"
if [[ "$USE_DOCKER_MYSQL" == "1" ]]; then
  if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
    cat >&2 <<'MSG'
Docker Compose is required because USE_DOCKER_MYSQL=1 in .env.
On a MacBook Air M2, install and start Docker Desktop for Apple silicon,
then rerun this script. Alternatively, set USE_DOCKER_MYSQL=0 and configure
MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD and MYSQL_DATABASE for
an existing MySQL 8.x server.
MSG
    exit 1
  fi
  if ! docker info >/dev/null 2>&1; then
    echo "Docker Desktop is installed but is not running. Open Docker Desktop, wait until it says Engine running, then rerun." >&2
    exit 1
  fi
  docker compose up -d db
else
  echo "Using the existing MySQL service configured in .env."
fi
python scripts/wait_for_mysql.py
python scripts/init_db.py
python scripts/import_dataset.py
if [[ ! -f models/predictive_models.joblib ]]; then python scripts/train_models.py; fi
python scripts/check_project.py --with-db
exec python run.py
