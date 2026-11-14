@echo off
title Installing ClipDrop
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if errorlevel 1 (
  echo.
  echo Something went wrong. Take a screenshot of this window and send it to Claude.
  pause
)
