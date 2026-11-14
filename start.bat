@echo off
rem Runs ClipDrop with a console window, handy for seeing error messages.
rem For normal use, open ClipDrop from the Start Menu instead.
title ClipDrop (debug window)
cd /d "%~dp0"
set PY=runtime\python\python.exe
if not exist "%PY%" (
  echo ClipDrop isn't installed yet. Double-click "Install ClipDrop.bat" first.
  pause
  exit /b
)
"%PY%" clipdrop.py %*
pause
