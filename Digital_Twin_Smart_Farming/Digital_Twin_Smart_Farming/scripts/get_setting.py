"""Print one value from the project's .env file for shell launch scripts."""
from pathlib import Path
import sys
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
key = sys.argv[1] if len(sys.argv) > 1 else ""
allowed = {"USE_DOCKER_MYSQL", "MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_DATABASE"}
if key not in allowed:
    raise SystemExit("Unsupported setting")
print((dotenv_values(ROOT / ".env").get(key) or "").strip())
