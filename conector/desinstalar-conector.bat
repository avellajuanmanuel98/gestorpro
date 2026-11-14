@echo off
REM Conector de Miga: lo detiene y lo quita del inicio de Windows.
title Desinstalar Conector de Miga
del /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\MigaConector.vbs" 2>nul
powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='powershell.exe'\" | Where-Object { $_.CommandLine -like '*MigaConector.ps1*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
rmdir /s /q "%LOCALAPPDATA%\MigaConector" 2>nul
echo El Conector de Miga fue desinstalado. Miga vuelve a abrir el cajon imprimiendo una tirita.
pause
