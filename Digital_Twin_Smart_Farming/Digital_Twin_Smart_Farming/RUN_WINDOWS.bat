@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Digital Twin for Smart Farming

if not exist ".venv\Scripts\python.exe" (
  echo First-time setup is required.
  call setup_windows.bat
  if errorlevel 1 exit /b 1
)
call ".venv\Scripts\activate.bat"

if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo Created .env. Review it before continuing.
)

for /f %%D in ('python scripts\get_setting.py USE_DOCKER_MYSQL') do set USE_DOCKER_MYSQL=%%D
if "%USE_DOCKER_MYSQL%"=="1" (
  where docker >nul 2>nul
  if not errorlevel 1 (
    docker compose version >nul 2>nul
    if not errorlevel 1 (
      echo Starting the MySQL database with Docker Compose...
      docker compose up -d db
      if errorlevel 1 (
        echo Docker database startup failed. Confirm Docker Desktop is running.
        pause
        exit /b 1
      )
    ) else (
      echo Docker Compose not found. A local MySQL server must already be running.
    )
  ) else (
    echo Docker not found. A local MySQL server must already be running.
  )
) else (
  echo Using the existing MySQL service configured in .env.
)

echo.
python scripts\wait_for_mysql.py
if errorlevel 1 goto :dbfailed

echo Initializing MySQL schema...
python scripts\init_db.py
if errorlevel 1 goto :dbfailed

echo Importing the bundled EcoIrrigate observations (safe to rerun)...
python scripts\import_dataset.py
if errorlevel 1 goto :dbfailed

if not exist "models\predictive_models.joblib" (
  echo Training missing local prediction model artifacts...
  python scripts\train_models.py
  if errorlevel 1 goto :dbfailed
)

echo Running local project checks...
python scripts\check_project.py --with-db
if errorlevel 1 goto :dbfailed

echo.
echo ============================================================
echo  APPLICATION STARTING
echo  Open: http://127.0.0.1:5000
echo  Keep this terminal window open while using the app.
echo ============================================================
python run.py
exit /b %errorlevel%

:dbfailed
echo.
echo Setup could not complete. Check MySQL host, port, user and password in .env.
echo For Docker Compose, set USE_DOCKER_MYSQL=1 (default); port 3307 and password dt_smart_farming_local.
echo For existing local MySQL/XAMPP, set USE_DOCKER_MYSQL=0, MYSQL_PORT=3306 and its actual password.
pause
exit /b 1
