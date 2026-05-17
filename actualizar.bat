@echo off
cd /d "%~dp0"

REM Opcional: descomenta y pega tu API key de football-data.org
REM (registrarse gratis en https://www.football-data.org/)
REM set FOOTBALL_DATA_KEY=TU_KEY_AQUI

echo Actualizando predicciones del Mundial 2026...
python src/predictor.py

echo.
echo Abriendo dashboard...
start mundial2026_predictor.html

echo Listo!
pause
