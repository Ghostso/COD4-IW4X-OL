# CODOLLauncher PowerShell fast-path
#
# The same flow as the C++ launcher, intended for machines without cl.exe:
#   - locate game from .ini
#   - create suspended process
#   - create TCLS_SHAREDMEMEMORY+GamePID if enabled
#   - resume
#   - monitor modules with psapi
#   - report BOOT_DEPTH
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\CODOLLauncher.ps1 -Diagnostic

param(
  [switch]$Diagnostic,
  [switch]$Verbose,
  [switch]$Wait,
  [switch]$NoMonitor
)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $scriptDir
$ini = Join-Path $scriptDir 'config\CODOLLauncher.ini'
$logDir = Join-Path $scriptDir 'logs'
$null = New-Item -ItemType Directory -Force -Path $logDir

function Get-IniValue {
  param($Section, $Key, $Default='')
  if (-not (Test-Path -LiteralPath $ini)) { return $Default }
  $match = Select-String -LiteralPath $ini -Pattern "^\[$Section\]" | Select-Object -First 1
  if (-not $match) { return $Default }
  $lines = Get-Content -LiteralPath $ini
  $start = $match.LineNumber
  for ($i=$start; $i -lt $lines.Count; $i++) {
    $line = $lines[$i]
    if ($line -and $line.StartsWith('[')) { break }
    if ($line -match "^$Key\s*=\s*(.*)$") { return $Matches[1] }
  }
  return $Default
}

$gameRel = Get-IniValue 'Game' 'Path' 'codoMP_client_shipRetail.exe'
$wdRel = Get-IniValue 'Game' 'WorkingDirectory' '.'
$args = Get-IniValue 'Launch' 'Arguments' ''
$monitorEnabled = Get-IniValue 'Monitor' 'Enabled' 'true'
$tclsEnabled = Get-IniValue 'TCLS' 'Enabled' 'false'

if ($NoMonitor) { $monitorEnabled = 'false' }
if (Test-Path -LiteralPath $gameRel) {
  $gamePath = (Resolve-Path -LiteralPath $gameRel).Path
} else {
  $gamePath = Join-Path $root $gameRel
  if (-not (Test-Path -LiteralPath $gamePath)) {
    Write-Error "Game not found: $gamePath"
    exit 2
  }
}
if ((Test-Path -LiteralPath $wdRel) -and (Get-Item -LiteralPath $wdRel).PSIsContainer) {
  $wd = (Resolve-Path -LiteralPath $wdRel).Path
} else {
  $wd = $root
}

$launcherPid = $PID
$exitTerm = 0
$game = $null
$mapping = $null
$view = $null

try {
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $gamePath
  $psi.WorkingDirectory = $wd
  $psi.UseShellExecute = $false
  if ($args) { $psi.Arguments = $args }
  $psi.CreateNoWindow = $true

  # Start suspended. PowerShell/Process does not expose CREATE_SUSPENDED, so
  # this path uses the Win32 API directly.
  Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class NativeLauncher {
  [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
  public static extern bool CreateProcessW(
    string? appName, string? commandLine, IntPtr processAttributes,
    IntPtr threadAttributes, bool inheritHandles, uint creationFlags,
    IntPtr environment, string? currentDirectory,
    ref STARTUPINFO startupInfo, out PROCESS_INFORMATION processInformation);

  [DllImport("kernel32.dll", SetLastError=true)]
  public static extern bool ResumeThread(IntPtr thread);

  [DllImport("kernel32.dll", SetLastError=true)]
  public static extern uint CreateFileMappingW(IntPtr file, IntPtr attributes,
    uint protect, uint highSize, uint lowSize, string name);

  [DllImport("kernel32.dll", SetLastError=true)]
  public static extern IntPtr MapViewOfFile(IntPtr mapping, uint access,
    uint offsetHigh, uint offsetLow, UIntPtr bytesToMap);

  [DllImport("kernel32.dll", SetLastError=true)]
  public static extern bool CloseHandle(IntPtr handle);

  [DllImport("kernel32.dll", SetLastError=true)]
  public static extern bool UnmapViewOfFile(IntPtr address);

  [DllImport("kernel32.dll", SetLastError=true)]
  public static extern uint WaitForSingleObject(IntPtr handle, uint ms);

  [DllImport("kernel32.dll", SetLastError=true)]
  public static extern bool GetExitCodeProcess(IntPtr process, out uint code);

  [StructLayout(LayoutKind.Sequential)]
  public struct STARTUPINFO {
    public int cb;
    public string? lpReserved;
    public string? lpDesktop;
    public string? lpTitle;
    public int dwX;
    public int dwY;
    public int dwXSize;
    public int dwYSize;
    public int dwXCountChars;
    public int dwYCountChars;
    public int dwFillAttribute;
    public int dwFlags;
    public short wShowWindow;
    public short cbReserved2;
    public IntPtr lpReserved2;
    public IntPtr hStdInput;
    public IntPtr hStdOutput;
    public IntPtr hStdError;
  }

  [StructLayout(LayoutKind.Sequential)]
  public struct PROCESS_INFORMATION {
    public IntPtr hProcess;
    public IntPtr hThread;
    public uint dwProcessId;
    public uint dwThreadId;
  }
}
"@

  $si = New-Object NativeLauncher+STARTUPINFO
  $si.cb = [System.Runtime.InteropServices.Marshal]::SizeOf($si)
  $pi = New-Object NativeLauncher+PROCESS_INFORMATION
  $cmd = "`"$gamePath`""
  if ($args) { $cmd += " $args" }

  # CREATE_SUSPENDED
  $ok = [NativeLauncher]::CreateProcessW($null, $cmd, [IntPtr]::Zero,
    [IntPtr]::Zero, $false, 4, [IntPtr]::Zero, $wd, [ref]$si, [ref]$pi)
  if (-not $ok) {
    $exitTerm = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
    Write-Host "[CreateProcessW] ERROR $exitTerm $gamePath"
    exit 4
  }
  $game = $pi.hProcess
  $thread = $pi.hThread
  $gamePid = $pi.dwProcessId
  $tid = $pi.dwThreadId

  if ($tclsEnabled -eq 'true') {
    $mappingName = "TCLS_SHAREDMEMEMORY+$gamePid"
    $mapping = [NativeLauncher]::CreateFileMappingW([IntPtr]::Zero, [IntPtr]::Zero,
      0x04, 0, 0x10000, $mappingName)
    if ($mapping -ne [IntPtr]::Zero) {
      $view = [NativeLauncher]::MapViewOfFile($mapping, 0x0006, 0, 0, [UIntPtr]0x10000)
    }
  } else {
    $mappingName = 'NONE'
  }

  $null = [NativeLauncher]::ResumeThread($thread)
  $null = [NativeLauncher]::CloseHandle($thread)

  if ($Diagnostic) {
    Write-Host "[Launcher]"
    Write-Host "PID=$launcherPid"
    Write-Host ""
    Write-Host "[Game]"
    Write-Host "PID=$gamePid"
    Write-Host "TID=$tid"
    Write-Host ""
    Write-Host "[Context]"
    Write-Host "TCLS=$tclsEnabled"
    Write-Host "Mapping=$mappingName"
  }

  if ($monitorEnabled -ne 'false') {
    $modules = @()
    for ($i=0; $i -lt 24; $i++) {
      Start-Sleep -Milliseconds 250
      $modules = @(Get-Process -Id $gamePid -ErrorAction SilentlyContinue).Modules |
        Where-Object { $_.ModuleName -match 'codoMP|TenProxy|TenRpcs|GameRpcs|TCJ|libcef|GbSpy|BugTrace|Base' } |
        Select-Object ModuleName, FileName, BaseAddress, ModuleMemorySize
      if ($modules.Count -gt 0) { break }
    }
    if ($Diagnostic) {
      Write-Host ""
      Write-Host "[Modules]"
      $modules | ForEach-Object { Write-Host "Module=$($_.FileName) 0x$($_.BaseAddress.ToString('X')) 0x$($_.ModuleMemorySize.ToString('X'))" }
    }
  }

  if ($Wait) {
    $null = [NativeLauncher]::WaitForSingleObject($game, 0xFFFFFFFF)
  }

  $exitCode = 0
  $null = [NativeLauncher]::GetExitCodeProcess($game, [ref]$exitCode)

  $depth = 0
  if ($modules) {
    $base = $modules | Where-Object { $_.ModuleName -ieq 'codoMP_client_shipRetailBase.dll' }
    $exe = $modules | Where-Object { $_.ModuleName -ieq 'codoMP_client_shipRetail.exe' }
    $tp = $modules | Where-Object { $_.ModuleName -imatch 'TenProxy|TenRpcs|GameRpcs|TCJ' }
    if ($base) { $depth = 2 }
    if ($tp) { $depth = 5 }
  }

  if ($Diagnostic) {
    Write-Host ""
    Write-Host "[Result]"
    Write-Host "BOOT_DEPTH=$depth"
    Write-Host "EXIT_CODE=$exitCode"
  } else {
    Write-Host "BOOT_DEPTH = $depth"
    Write-Host "GamePID = $gamePid"
  }

  $log = Join-Path $logDir ("CODOLLauncher_" + (Get-Date -Format 'yyyyMMdd-HHmmss') + ".log")
  "[Launcher] PID=$launcherPid" | Set-Content -LiteralPath $log
  "[Launcher] BOOT_DEPTH=$depth" | Add-Content -LiteralPath $log
  "[Game] PID=$gamePid" | Add-Content -LiteralPath $log
  "[Game] TID=$tid" | Add-Content -LiteralPath $log
  "[Game] EXIT_CODE=$exitCode" | Add-Content -LiteralPath $log
  "[Context] TCLS=$tclsEnabled Mapping=$mappingName" | Add-Content -LiteralPath $log

  if ($view -ne [IntPtr]::Zero) { $null = [NativeLauncher]::UnmapViewOfFile($view) }
  if ($mapping -ne [IntPtr]::Zero) { $null = [NativeLauncher]::CloseHandle($mapping) }
  if ($game -ne [IntPtr]::Zero) { $null = [NativeLauncher]::CloseHandle($game) }
  exit $exitTerm
} catch {
  Write-Host $_
  exit 1
}
