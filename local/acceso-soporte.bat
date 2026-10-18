@echo off
REM GestorPro - edicion local: crea o habilita el acceso de soporte de GestorPro (consola de plataforma).
cd /d "%~dp0.."
if not exist "venv\Scripts\python.exe" (echo [ERROR] GestorPro no esta instalado. Ejecuta 1-instalar.bat & pause & exit /b 1)
title GestorPro
venv\Scripts\python.exe scripts\local_edition.py soporte
pause
