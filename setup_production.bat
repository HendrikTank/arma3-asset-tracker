@echo off
REM Production Deployment Setup Script for Windows
REM This script helps set up the production environment on Windows

echo ================================================
echo ARMA3 Asset Tracker - Production Setup (Windows)
echo ================================================
echo.

REM Check if .env exists
if exist .env (
    echo WARNING: .env file already exists!
    set /p OVERWRITE="Do you want to overwrite it? (y/N): "
    if /i not "%OVERWRITE%"=="y" (
        echo Keeping existing .env file
        goto :skip_env
    )
)

echo Creating .env file from template...
copy .env.example .env

echo.
echo Generating secure secret key...
python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))" > temp_key.txt
for /f "delims=" %%i in (temp_key.txt) do set NEW_KEY=%%i
del temp_key.txt

REM Update the .env file with the new key
powershell -Command "(Get-Content .env) -replace 'SECRET_KEY=your-secret-key-here-change-me', '%NEW_KEY%' | Set-Content .env"

echo [OK] .env file created with secure secret key

:skip_env

echo.
echo ================================================
echo Configuration Steps
echo ================================================
echo.
echo Please complete the following configuration:
echo.
echo 1. Edit .env file and update:
echo    - POSTGRES_PASSWORD (line 33)
echo    - DATABASE_URL with your PostgreSQL password
echo    - Your domain name (if known)
echo.
echo 2. Edit docker-compose.prod.yml and update:
echo    - Line 36: Replace 'your-domain.com' with your actual domain
echo.
echo 3. Ensure Traefik is running:
echo    - Create network: docker network create traefik_network
echo.

pause

echo.
echo ================================================
echo Deployment
echo ================================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running
    echo Please start Docker Desktop and run this script again
    pause
    exit /b 1
)

echo [OK] Docker is running

REM Check if traefik network exists
docker network inspect traefik_network >nul 2>&1
if errorlevel 1 (
    echo WARNING: traefik_network does not exist
    set /p CREATE_NET="Create traefik_network now? (Y/n): "
    if /i not "%CREATE_NET%"=="n" (
        docker network create traefik_network
        echo [OK] Created traefik_network
    ) else (
        echo WARNING: You must create traefik_network before deployment
    )
)

echo.
set /p BUILD="Build and start containers? (y/N): "
if /i not "%BUILD%"=="y" goto :skip_build

echo Building containers...
docker-compose -f docker-compose.prod.yml build

echo.
echo Starting containers...
docker-compose -f docker-compose.prod.yml up -d

echo.
echo Waiting for services to be healthy...
timeout /t 10 /nobreak >nul

REM Check container status
docker-compose -f docker-compose.prod.yml ps

echo.
echo [OK] Containers started

echo.
echo ================================================
echo Database Setup
echo ================================================
echo.

set /p INIT_DB="Initialize database migrations? (Y/n): "
if /i "%INIT_DB%"=="n" goto :skip_db

echo Initializing Flask-Migrate...
docker-compose -f docker-compose.prod.yml exec -T web flask db init 2>nul || echo Migrations already initialized

echo Creating initial migration...
docker-compose -f docker-compose.prod.yml exec -T web flask db migrate -m "Initial migration"

echo Applying migration...
docker-compose -f docker-compose.prod.yml exec -T web flask db upgrade

echo [OK] Database migrations complete

:skip_db

echo.
set /p CREATE_ADMIN="Create admin user? (Y/n): "
if /i "%CREATE_ADMIN%"=="n" goto :skip_admin

docker-compose -f docker-compose.prod.yml exec web python create_admin.py

:skip_admin

echo.
echo ================================================
echo Deployment Complete!
echo ================================================
echo.
echo Your application should now be running at:
echo   https://your-domain.com
echo.
echo Health check endpoints:
echo   https://your-domain.com/health
echo   https://your-domain.com/ready
echo.
echo To view logs:
echo   docker-compose -f docker-compose.prod.yml logs -f
echo.
echo For troubleshooting, see:
echo   - README.md
echo   - DEPLOYMENT.md
echo   - MIGRATIONS.md
echo.
goto :end

:skip_build

echo.
echo Deployment cancelled. To deploy manually:
echo   docker-compose -f docker-compose.prod.yml up -d --build
echo.
echo See DEPLOYMENT.md for detailed instructions

:end

echo.
echo [OK] Setup script complete!
pause
