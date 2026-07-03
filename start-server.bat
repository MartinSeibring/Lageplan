@echo off
REM ── Radar-Server starten (Windows) ─────────────────────────
REM Doppelklick genügt. Fenster offen lassen, solange der
REM Lageplan genutzt wird. Beenden mit Strg+C oder Fenster schließen.

cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo FEHLER: Python ist nicht installiert oder nicht im PATH.
  echo Bitte von https://www.python.org/downloads/ installieren.
  pause
  exit /b 1
)

echo Pruefe/installiere Python-Pakete ...
python -m pip install -q -r requirements.txt

echo.
echo Starte Radar-Server auf http://localhost:5050 ...
echo (Dieses Fenster offen lassen!)
echo.
python server.py
pause
