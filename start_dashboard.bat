@echo off
title KongTrade Dashboard
cd /d "%~dp0"

:loop
echo.
echo [%date% %time%] KongTrade Dashboard wird gestartet...
echo =====================================================

python dashboard.py

set EXIT_CODE=%ERRORLEVEL%

if %EXIT_CODE% == 0 (
    echo [%date% %time%] Dashboard sauber beendet (Ctrl+C). Kein Neustart.
    goto end
)

echo.
echo [%date% %time%] Dashboard beendet mit Code %EXIT_CODE%.
echo Automatischer Neustart in 5 Sekunden... (Ctrl+C zum Abbrechen)
echo.
timeout /t 5 /nobreak >nul

goto loop

:end
echo.
echo Dashboard gestoppt. Fenster schliessen mit beliebiger Taste.
pause >nul
