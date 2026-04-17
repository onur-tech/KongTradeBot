@echo off
title KongTrade Watchdog
cd /d "%~dp0"
echo [watchdog] Starte KongTrade Watchdog...
echo [watchdog] Druecke Ctrl+C zum Beenden
echo.
python utils\watchdog.py
pause
