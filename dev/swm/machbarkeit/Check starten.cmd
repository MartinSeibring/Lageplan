@echo off
rem Startet den PowerShell-Check ohne die Ausfuehrungsrichtlinie dauerhaft zu aendern
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0check.ps1"
echo.
pause
