@echo off
REM ============================================================================
REM  GestorPro / Miga - INICIAR
REM  Arranca la base de datos, el backend (puerto 8000) y el frontend (5173),
REM  y abre el navegador. Para detenerlo, cierra las ventanas que se abren.
REM  Si es la primera vez, ejecuta antes instalar.bat
REM ============================================================================
setlocal
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
  echo [ERROR] Primero ejecuta instalar.bat
  pause & exit /b 1
)
venv\Scripts\python.exe scripts\dev_local.py start
pause
