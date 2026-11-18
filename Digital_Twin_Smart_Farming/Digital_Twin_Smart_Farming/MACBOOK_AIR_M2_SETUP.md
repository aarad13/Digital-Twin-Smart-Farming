# MacBook Air M2 setup guide (Apple silicon)

This project supports an Apple-silicon Mac. The simplest route is to run the
whole application in Docker; you do **not** need to install Python or MySQL on
your Mac for that route. Docker Desktop provides the local container engine.

## Route A — recommended: run the entire project with Docker

1. Download **Docker Desktop for Mac with Apple silicon** from the official
   [Docker installation page](https://docs.docker.com/desktop/setup/install/mac-install/).
   Do not choose the Intel download. Install Docker Desktop, open it, and wait
   until its status indicates that the engine is running. Docker's current Mac
   requirements include a supported macOS version and at least 4 GB RAM.
2. Extract `Digital_Twin_Smart_Farming_Project.zip` to a normal writable folder.
3. Open that folder in VS Code. Choose **Terminal → New Terminal**. Confirm the
   terminal is in the folder containing `docker-compose.yml`.
4. Run:

   ```bash
   docker compose up --build
   ```

   Docker Compose builds the Flask service, starts MySQL 8.4, waits for the DB,
   creates the tables, imports the included experimental dataset, executes the
   project checks and starts Flask. The images are selected for the host's
   architecture; this project does not force Intel/amd64 emulation on your M2.
5. Open **http://127.0.0.1:5000** in Safari or Chrome. Keep the terminal open
   while using the app.
6. Stop with `Ctrl+C`. For a later stop/start, use `docker compose down` and
   `docker compose up`. The database volume is retained when using `down`.
   `docker compose down -v` deletes the database volume and all local DB data.

Useful Docker commands (run in the project folder):

```bash
# Check running services
docker compose ps

# Follow application and database logs
docker compose logs -f web db

# Start again after the first build
docker compose up

# Stop containers without deleting the DB volume
docker compose down
```

## Route B — run Flask natively; keep MySQL in Docker

Use this route if you want the Python backend running directly on macOS while
MySQL stays in a container.

1. Install a native Apple-silicon Python 3.12 from the
   [official macOS Python downloads](https://www.python.org/downloads/macos/).
   Python's universal2 macOS builds run on Apple silicon; ensure the selected
   interpreter reports `arm64` so the virtual environment is not Intel/Rosetta.
2. Install and start Docker Desktop for Apple silicon as described above.
3. In VS Code Terminal, from the project folder, run:

   ```bash
   PYTHON_BIN=python3.12 ./setup_mac_linux.sh
   ./run_mac_linux.sh
   ```

   The setup creates `.venv`, installs the pinned Python requirements and makes
   a local `.env` from `.env.example`. The run script starts the MySQL container,
   waits for it, initializes the schema, imports the dataset, runs checks and
   starts Flask. Open **http://127.0.0.1:5000**.

If `python3.12` is not found, install Python 3.12 first and open a new Terminal.
To check the interpreter architecture:

```bash
python3.12 -c 'import platform, sys; print(sys.version); print(platform.machine())'
```

On your M2 Mac, `platform.machine()` should print `arm64`. If it prints
`x86_64`, check that Terminal is not running under Rosetta and install/use the
Apple-silicon Python installer.

## Using an existing MySQL server instead

Edit `.env` and set `USE_DOCKER_MYSQL=0`. Then set `MYSQL_HOST`, `MYSQL_PORT`,
`MYSQL_USER`, `MYSQL_PASSWORD` and `MYSQL_DATABASE` to match your MySQL 8.x
server. Start that server before running `./run_mac_linux.sh`.

## Troubleshooting

- **`Cannot connect to the Docker daemon`**: open Docker Desktop and wait for
  the engine to finish starting, then retry.
- **Port 5000 is already allocated**: change `APP_PORT` in `.env` (for Docker
  Route A) and open the new port, e.g. `http://127.0.0.1:5001`.
- **Port 3307 is already allocated**: change `MYSQL_PORT` in `.env` to an unused
  local port. Keep the internal container port at 3306; Compose handles this.
- **Python says `x86_64` on an M2**: do not reuse that `.venv`; install native
  Python 3.12, remove only the project's `.venv` folder, then rerun setup.
- **Regional search/map data does not load**: check internet access. Regional
  services, map tiles and some front-end libraries are external services.
- **App reports database errors**: run `docker compose ps` and
  `docker compose logs -f db web` to inspect service health and logs.

## What this setup does not prove

The included dataset is from two experimental Kolkata farm series, not a
nationally representative Indian dataset. Regional climate/soil values are
external gridded or modelled estimates, not field measurements. The app is a
research/decision-support prototype: field soil tests and local agronomic review
are still required before operational fertilizer, pesticide or irrigation
recommendations. A successful local startup does not validate physical sensors,
pumps, field performance or agronomic outcomes.
