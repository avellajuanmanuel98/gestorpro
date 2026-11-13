@echo off
REM GestorPro - edicion local: restablece la contrasena olvidada de un usuario.
cd /d "%~dp0.."
if not exist "venv\Scripts\python.exe" (echo [ERROR] GestorPro no esta instalado. Ejecuta 1-instalar.bat & pause & exit /b 1)
title GestorPro
venv\Scripts\python.exe scripts\local_edition.py contrasena
pause
