"""Wait for the configured MySQL service to accept connections."""
from pathlib import Path
import os
import sys
import time
from dotenv import load_dotenv
import pymysql

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
host = os.getenv("MYSQL_HOST", "127.0.0.1")
port = int(os.getenv("MYSQL_PORT", "3307"))
user = os.getenv("MYSQL_USER", "root")
password = os.getenv("MYSQL_PASSWORD", "")
deadline = time.monotonic() + 90
last_error = None
while time.monotonic() < deadline:
    try:
        conn = pymysql.connect(host=host, port=port, user=user, password=password,
                               connect_timeout=3, read_timeout=3, write_timeout=3)
        conn.close()
        print(f"MySQL is accepting connections at {host}:{port}.")
        raise SystemExit(0)
    except Exception as exc:
        last_error = exc
        time.sleep(2)
print(f"MySQL did not become ready at {host}:{port}: {last_error}", file=sys.stderr)
raise SystemExit(1)
