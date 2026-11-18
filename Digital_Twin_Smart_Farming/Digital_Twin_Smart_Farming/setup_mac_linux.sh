#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Apple-silicon Macs should use a native ARM64 Python, not an Intel/Rosetta Python.
PYTHON_BIN="${PYTHON_BIN:-python3}"
IS_APPLE_SILICON=0
if [[ "$(uname -s)" == "Darwin" ]]; then
  # sysctl detects Apple silicon even when Terminal itself is running under Rosetta.
  if [[ "$(/usr/sbin/sysctl -n hw.optional.arm64 2>/dev/null || echo 0)" == "1" ]]; then
    IS_APPLE_SILICON=1
  fi
fi
if [[ "$IS_APPLE_SILICON" == "1" ]]; then
  PYTHON_ARCH="$($PYTHON_BIN -c 'import platform; print(platform.machine())' 2>/dev/null || true)"
  if [[ "$PYTHON_ARCH" != "arm64" ]]; then
    cat >&2 <<'MSG'
This is an Apple-silicon Mac, but the selected Python is not running as arm64.
Install a native Apple-silicon Python 3.12, open a native Terminal (not Rosetta),
and run:
  PYTHON_BIN=python3.12 ./setup_mac_linux.sh
Do not use an Intel/Rosetta Python for this virtual environment.
MSG
    exit 1
  fi
fi

"$PYTHON_BIN" - <<'PY'
import platform
import sys
if sys.version_info < (3, 11) or sys.version_info >= (3, 14):
    raise SystemExit(
        "Use Python 3.11, 3.12 or 3.13. Python 3.12 is the recommended version."
    )
print(f"Using Python {sys.version.split()[0]} ({platform.machine()})")
PY

if [[ -x .venv/bin/python ]]; then
  VENV_ARCH="$(.venv/bin/python -c 'import platform; print(platform.machine())')"
  if [[ "$IS_APPLE_SILICON" == "1" && "$VENV_ARCH" != "arm64" ]]; then
    cat >&2 <<'MSG'
The existing .venv was created with a non-ARM Python and cannot be reused on
this Apple-silicon setup. Remove only the project's .venv folder, then rerun:
  PYTHON_BIN=python3.12 ./setup_mac_linux.sh
MSG
    exit 1
  fi
else
  "$PYTHON_BIN" -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if [[ ! -f .env ]]; then cp .env.example .env; fi

echo
echo "Setup complete. Review .env, then run ./run_mac_linux.sh"
