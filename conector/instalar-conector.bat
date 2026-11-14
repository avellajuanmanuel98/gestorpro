@echo off
REM Conector de Miga: instala el programa que abre el cajon monedero sin imprimir.
REM No necesita permisos de administrador. Queda arrancando solo al prender el equipo.
title Instalar Conector de Miga
set "DEST=%LOCALAPPDATA%\MigaConector"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

if not exist "%~dp0MigaConector.ps1" (
  echo [ERROR] No encuentro MigaConector.ps1 junto a este archivo. Descomprime todo el ZIP primero.
  pause & exit /b 1
)

echo Instalando el Conector de Miga en %DEST% ...
if not exist "%DEST%" mkdir "%DEST%"
copy /y "%~dp0MigaConector.ps1" "%DEST%\MigaConector.ps1" >nul

REM Lanzador invisible (sin ventana negra) para el inicio de Windows
> "%DEST%\iniciar-conector.vbs" echo CreateObject("WScript.Shell").Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""%DEST%\MigaConector.ps1""", 0, False
copy /y "%DEST%\iniciar-conector.vbs" "%STARTUP%\MigaConector.vbs" >nul

echo Arrancando el conector...
wscript.exe "%DEST%\iniciar-conector.vbs"
timeout /t 4 /nobreak >nul

powershell.exe -NoProfile -Command "try { $r = Invoke-RestMethod -Uri 'http://127.0.0.1:17777/estado' -TimeoutSec 3; if ($r.ok) { exit 0 } else { exit 1 } } catch { exit 1 }"
if errorlevel 1 (
  echo.
  echo [ATENCION] El conector no respondio. Revisa el archivo %DEST%\conector.log
  echo y envia una foto a soporte.
) else (
  echo.
  echo ============================================================
  echo  Listo: el Conector de Miga esta funcionando.
  echo  Arrancara solo cada vez que se prenda el computador.
  echo  En Miga, la primera vez, Chrome puede pedir permiso: Permitir.
  echo ============================================================
)
echo.
pause
