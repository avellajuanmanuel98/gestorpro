# Conector de Miga / GestorPro - abre el cajon monedero sin imprimir.
#
# Chrome no deja que una pagina web mande comandos directos a la impresora. Este programa
# pequeno corre en el computador de la caja, escucha SOLO en este mismo equipo (127.0.0.1) y,
# cuando Miga se lo pide, le manda a la impresora el comando ESC/POS de abrir el cajon
# (ESC p): el cajon se abre y no sale papel. Es lo mismo que hacia el programa de caja anterior.
#
# Seguridad: solo escucha en 127.0.0.1 (nadie de la red lo ve), solo acepta pedidos de la
# direccion de Miga (lista ALLOWED_ORIGINS) y solo sabe hacer una cosa: abrir el cajon.
#
# Uso: lo arranca instalar-conector.bat (y queda arrancando solo al prender el equipo).
# Archivo en ASCII a proposito: Windows PowerShell 5.1 lee los .ps1 sin BOM como ANSI.

param(
  [int]$Port = 17777,
  # Vacio = automatico: "Generic / Text Only" si existe (deja pasar comandos tal cual), si no POS-80C
  [string]$Printer = '',
  # 0 = cajon #1 (pin 2), 1 = cajon #2 (pin 5)
  [int]$Pin = 0
)

$ErrorActionPreference = 'Stop'
$ALLOWED_ORIGINS = @(
  'https://gestorpro-rxy5.onrender.com',
  'http://localhost:5173',
  'http://127.0.0.1:8000',
  'http://localhost:8000'
)
$VERSION = '1.0'
$LOG = Join-Path $PSScriptRoot 'conector.log'

function Write-Log([string]$msg) {
  try { Add-Content -Path $LOG -Value ("{0}  {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg) } catch {}
}

# Impresion en crudo (RAW) por la API de Windows: los bytes llegan a la impresora tal cual.
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public static class MigaRawPrinter {
  [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
  public class DOCINFO {
    [MarshalAs(UnmanagedType.LPWStr)] public string pDocName;
    [MarshalAs(UnmanagedType.LPWStr)] public string pOutputFile;
    [MarshalAs(UnmanagedType.LPWStr)] public string pDataType;
  }
  [DllImport("winspool.drv", EntryPoint = "OpenPrinterW", SetLastError = true, CharSet = CharSet.Unicode)]
  static extern bool OpenPrinter(string name, out IntPtr handle, IntPtr defaults);
  [DllImport("winspool.drv", SetLastError = true)]
  static extern bool ClosePrinter(IntPtr handle);
  [DllImport("winspool.drv", EntryPoint = "StartDocPrinterW", SetLastError = true, CharSet = CharSet.Unicode)]
  static extern int StartDocPrinter(IntPtr handle, int level, [In] DOCINFO info);
  [DllImport("winspool.drv", SetLastError = true)]
  static extern bool EndDocPrinter(IntPtr handle);
  [DllImport("winspool.drv", SetLastError = true)]
  static extern bool StartPagePrinter(IntPtr handle);
  [DllImport("winspool.drv", SetLastError = true)]
  static extern bool EndPagePrinter(IntPtr handle);
  [DllImport("winspool.drv", SetLastError = true)]
  static extern bool WritePrinter(IntPtr handle, byte[] data, int count, out int written);

  public static void Send(string printer, byte[] data) {
    IntPtr h;
    if (!OpenPrinter(printer, out h, IntPtr.Zero))
      throw new Exception("No se pudo abrir la impresora '" + printer + "' (error " + Marshal.GetLastWin32Error() + ")");
    try {
      DOCINFO info = new DOCINFO();
      info.pDocName = "Miga - abrir cajon";
      info.pDataType = "RAW";
      if (StartDocPrinter(h, 1, info) == 0)
        throw new Exception("StartDocPrinter fallo (error " + Marshal.GetLastWin32Error() + ")");
      try {
        StartPagePrinter(h);
        int written;
        if (!WritePrinter(h, data, data.Length, out written) || written != data.Length)
          throw new Exception("WritePrinter fallo (error " + Marshal.GetLastWin32Error() + ")");
        EndPagePrinter(h);
      } finally { EndDocPrinter(h); }
    } finally { ClosePrinter(h); }
  }
}
'@

function Get-TargetPrinter {
  if ($Printer) { return $Printer }
  $names = @(Get-CimInstance -ClassName Win32_Printer | ForEach-Object { $_.Name })
  foreach ($candidate in @('Generic / Text Only', 'POS-80C', 'POS-80')) {
    if ($names -contains $candidate) { return $candidate }
  }
  throw 'No encontre la impresora de tickets (ni "Generic / Text Only" ni "POS-80C"). Indicala con -Printer "Nombre".'
}

function Open-Drawer {
  $target = Get-TargetPrinter
  # ESC p m t1 t2: pulso de 50 ms (t1=25 x 2 ms) y espera de 500 ms (t2=250 x 2 ms)
  [byte[]]$kick = 0x1B, 0x70, [byte]$Pin, 0x19, 0xFA
  [MigaRawPrinter]::Send($target, $kick)
  return $target
}

function Send-Response($stream, [int]$status, [string]$reason, [string]$origin, [string]$body) {
  $headers = "HTTP/1.1 $status $reason`r`n"
  if ($origin) {
    $headers += "Access-Control-Allow-Origin: $origin`r`n"
    $headers += "Vary: Origin`r`n"
    $headers += "Access-Control-Allow-Methods: GET, POST, OPTIONS`r`n"
    $headers += "Access-Control-Allow-Headers: Content-Type`r`n"
    # Chrome pide permiso a la pagina publica para hablar con este equipo (red local/loopback)
    $headers += "Access-Control-Allow-Private-Network: true`r`n"
    $headers += "Access-Control-Max-Age: 600`r`n"
  }
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
  $headers += "Content-Type: application/json; charset=utf-8`r`n"
  $headers += "Content-Length: $($bytes.Length)`r`n"
  $headers += "Cache-Control: no-store`r`n"
  $headers += "Connection: close`r`n`r`n"
  $head = [System.Text.Encoding]::ASCII.GetBytes($headers)
  $stream.Write($head, 0, $head.Length)
  if ($bytes.Length) { $stream.Write($bytes, 0, $bytes.Length) }
  $stream.Flush()
}

function Handle-Client($client) {
  $client.ReceiveTimeout = 3000
  $stream = $client.GetStream()
  $reader = New-Object System.IO.StreamReader($stream, [System.Text.Encoding]::ASCII, $false, 1024, $true)
  $requestLine = $reader.ReadLine()
  if (-not $requestLine) { return }
  $parts = $requestLine.Split(' ')
  $method = $parts[0]
  $path = if ($parts.Length -gt 1) { $parts[1].Split('?')[0] } else { '/' }
  $origin = ''
  while ($true) {
    $line = $reader.ReadLine()
    if ($null -eq $line -or $line -eq '') { break }
    if ($line -match '^(?i)origin:\s*(.+)$') { $origin = $Matches[1].Trim() }
  }
  $allowed = ($ALLOWED_ORIGINS -contains $origin)
  $echo = if ($allowed) { $origin } else { '' }

  # /estado se puede abrir en el navegador para comprobar que esta corriendo (no hace nada)
  if ($method -eq 'GET' -and $path -eq '/estado') {
    Send-Response $stream 200 'OK' $echo ('{"ok":true,"app":"miga-conector","version":"' + $VERSION + '"}')
    return
  }
  if (-not $allowed) {
    Send-Response $stream 403 'Forbidden' '' '{"ok":false,"error":"origen no permitido"}'
    Write-Log "Rechazado: origen '$origin' $method $path"
    return
  }
  if ($method -eq 'OPTIONS') { Send-Response $stream 204 'No Content' $echo ''; return }
  if ($method -eq 'POST' -and $path -eq '/cajon') {
    try {
      $target = Open-Drawer
      Send-Response $stream 200 'OK' $echo '{"ok":true}'
      Write-Log "Cajon abierto (impresora: $target)"
    } catch {
      $msg = ($_.Exception.Message -replace '"', "'")
      Send-Response $stream 500 'Error' $echo ('{"ok":false,"error":"' + $msg + '"}')
      Write-Log "ERROR al abrir el cajon: $msg"
    }
    return
  }
  Send-Response $stream 404 'Not Found' $echo '{"ok":false}'
}

# Una sola copia corriendo: si el puerto ya esta ocupado, otra copia ya atiende.
$listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $Port)
try { $listener.Start() } catch {
  Write-Log "El puerto $Port ya esta en uso: el conector ya estaba corriendo."
  exit 0
}
Write-Log "Conector $VERSION escuchando en 127.0.0.1:$Port"
while ($true) {
  $client = $listener.AcceptTcpClient()
  try { Handle-Client $client } catch { Write-Log "Error atendiendo un pedido: $($_.Exception.Message)" }
  finally { $client.Close() }
}
