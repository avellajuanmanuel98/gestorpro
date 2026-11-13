@echo off
REM GestorPro - edicion local: Abre GestorPro. Deja esta ventana abierta (minimizada) mientras se use.
cd /d "%~dp0.."
if not exist "venv\Scripts\python.exe" (echo [ERROR] GestorPro no esta instalado. Ejecuta 1-instalar.bat & pause & exit /b 1)
title GestorPro
venv\Scripts\python.exe scripts\local_edition.py iniciar
if errorlevel 1 pause
