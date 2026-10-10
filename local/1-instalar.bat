@echo off
REM ============================================================================
REM  GestorPro - EDICION LOCAL - INSTALAR (en el computador del negocio)
REM
REM  Requisitos en el equipo:
REM    - Python 3.12 o superior (python.org; marca "Add python.exe to PATH")
REM    - Git (git-scm.com), para poder actualizar despues
REM    - PostgreSQL: zip de binarios descomprimido en %USERPROFILE%\pgsql
REM  No necesita Node.js: la aplicacion ya viene compilada.
REM  Se puede ejecutar de nuevo sin perder datos.
REM ============================================================================
setlocal
cd /d "%~dp0.."

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY (
  echo [ERROR] No encontre Python. Instalalo desde https://www.python.org/downloads/
  echo         y marca la opcion "Add python.exe to PATH".
  pause & exit /b 1
)
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)"
if errorlevel 1 (
  echo [ERROR] Se necesita Python 3.12 o superior.
  pause & exit /b 1
)
if not exist "venv\Scripts\python.exe" (
  echo ==^> Creando el entorno de Python ...
  %PY% -m venv venv || (echo [ERROR] No se pudo crear el entorno. & pause & exit /b 1)
)
echo ==^> Instalando dependencias ...
venv\Scripts\python.exe -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (echo [ERROR] Fallo la instalacion de dependencias. & pause & exit /b 1)

venv\Scripts\python.exe scripts\local_edition.py instalar
pause
