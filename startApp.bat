@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "APP_NAME=Sales Data Exchange"
set "DATABASE_NAME=sales_data_exchange"
set "POSTGRES_SERVICE=postgres"
set "UV_CACHE_DIR=%CD%\.cache\uv"
set "DOCKER_DESKTOP=C:\Program Files\Docker\Docker\Docker Desktop.exe"
set "RUN_CHECKS=0"

if /I "%~1"=="--check" set "RUN_CHECKS=1"

echo.
echo ============================================================
echo  Starting %APP_NAME%
echo ============================================================
echo.

echo [1/6] Checking prerequisites...
where uv >nul 2>&1
if errorlevel 1 goto missing_uv

where docker >nul 2>&1
if errorlevel 1 goto missing_docker

if not exist "pyproject.toml" (
    echo ERROR: pyproject.toml was not found in %CD%.
    exit /b 1
)

if not exist ".env" if exist ".env.example" (
    copy /Y ".env.example" ".env" >nul
    echo Created .env from .env.example.
)

echo [2/6] Checking Docker Desktop...
docker info >nul 2>&1
if errorlevel 1 (
    if not exist "%DOCKER_DESKTOP%" goto docker_not_found
    echo Docker is not ready. Starting Docker Desktop...
    start "" "%DOCKER_DESKTOP%"
)

set /a DOCKER_ATTEMPTS=0
:wait_for_docker
docker info >nul 2>&1
if not errorlevel 1 goto docker_ready
set /a DOCKER_ATTEMPTS+=1
if %DOCKER_ATTEMPTS% GEQ 60 (
    echo ERROR: Docker did not become ready within 120 seconds.
    exit /b 1
)
timeout /t 2 /nobreak >nul
goto wait_for_docker

:docker_ready
echo [3/6] Starting PostgreSQL...
docker compose up -d --remove-orphans %POSTGRES_SERVICE%
if errorlevel 1 goto command_failed

set /a POSTGRES_ATTEMPTS=0
:wait_for_postgres
docker compose exec -T %POSTGRES_SERVICE% pg_isready -U postgres -d %DATABASE_NAME% >nul 2>&1
if not errorlevel 1 goto postgres_ready
set /a POSTGRES_ATTEMPTS+=1
if %POSTGRES_ATTEMPTS% GEQ 30 (
    echo ERROR: PostgreSQL did not become ready within 60 seconds.
    exit /b 1
)
timeout /t 2 /nobreak >nul
goto wait_for_postgres

:postgres_ready
echo [4/6] Synchronizing Python dependencies...
uv sync
if errorlevel 1 goto command_failed

echo [5/6] Applying database migrations...
uv run python -m alembic upgrade head
if errorlevel 1 goto command_failed

if "%RUN_CHECKS%"=="1" (
    echo Running Ruff and pytest checks...
    uv run python -m ruff check app tests alembic
    if errorlevel 1 goto command_failed
    uv run python -m pytest
    if errorlevel 1 goto command_failed
)

echo [6/6] Starting FastAPI...
echo.
echo Swagger UI: http://127.0.0.1:8000/docs
echo Press Ctrl+C to stop the API. PostgreSQL will remain running.
echo.
uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
exit /b %ERRORLEVEL%

:missing_uv
echo ERROR: uv is not installed or is not available on PATH.
echo Install it with: winget install --id=astral-sh.uv -e
exit /b 1

:missing_docker
echo ERROR: Docker is not installed or is not available on PATH.
exit /b 1

:docker_not_found
echo ERROR: Docker Desktop is not running and was not found at:
echo %DOCKER_DESKTOP%
exit /b 1

:command_failed
echo.
echo ERROR: Startup stopped because a command failed.
exit /b 1
