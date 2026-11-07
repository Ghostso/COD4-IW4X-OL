<#
    Build the CoDOL (sh1x) dedicated server.

    Run it yourself:   powershell -ExecutionPolicy Bypass -File tools\BUILD-CODOL.ps1

    This exists because three environment traps on this machine each make the
    build fail in a way that looks like a code error:

      1. gcc's default temp directory is C:\WINDOWS, which is not writable
         here -- "Cannot create temporary file in C:\WINDOWS\: Permission
         denied".  TMP/TEMP must point somewhere writable, and setting them
         from Git Bash does NOT reach gcc; it has to be the Windows
         environment, which is what this script does.
      2. msys2 must be on PATH or make dies with
         "make: echo: No such file or directory" before compiling anything.
      3. The default target LINKS, and ld DELETES its output when the link
         fails.  A bare `make` on 2026-09-17 destroyed bin\codol_dedrun.exe
         that way.  -ObjectsOnly below compiles without linking.

    WHAT IT WRITES.  The default target is bin\codol_dedrun.exe (makefile
    TARGETNAME=codol_dedrun).  It does NOT touch bin\codol_dedrun_next.exe,
    which is what START-CODOL-SERVER.cmd actually launches -- promote a new
    build to the live name yourself, deliberately, after it links:

        copy /y bin\codol_dedrun.exe bin\codol_dedrun_next.exe

    Keep a rollback copy first; bin\rollback\ is where previous ones live.
#>
param(
    # Compile every object but do not link. Safe to run at any time.
    [switch] $ObjectsOnly,
    # Parallel jobs. Lower it if a parallel build races on the shared obj dir.
    [int] $Jobs = 4,
    # Extra make arguments, e.g. -MakeArgs 'DEBUG=true'
    [string[]] $MakeArgs = @()
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$make = 'C:\msys64\usr\bin\make.exe'

if (-not (Test-Path $make)) {
    Write-Error "msys2 make not found at $make. Install msys2 or edit this script."
}

# Trap 1: a writable temp for gcc/nasm.
$tmp = Join-Path $repo 'obj\_tmp'
New-Item -ItemType Directory -Force $tmp | Out-Null
$env:TMP  = $tmp
$env:TEMP = $tmp

# Trap 2: msys2 tools ahead of anything else on PATH.
# mingw32/bin FIRST: both it and usr/bin ship a `windres`, and only the
# mingw32 one targets i686. usr/bin still supplies make, sh and coreutils.
$env:PATH = 'C:\msys64\mingw32\bin;C:\msys64\usr\bin;' + $env:PATH

$target = if ($ObjectsOnly) { 'objects-only' } else { 'default (links bin\codol_dedrun.exe)' }
Write-Host "repo    $repo"
Write-Host "target  $target"
Write-Host "jobs    $Jobs"
Write-Host ''

if ($ObjectsOnly) {
    # Trap 3: the makefile's `objects` target builds every object and never
    # links, so a failure here can never remove or replace a deployed binary.
    & $make -C $repo -j $Jobs @MakeArgs objects
} else {
    Write-Host "NOTE: this links, and a FAILED link deletes bin\codol_dedrun.exe." -ForegroundColor Yellow
    Write-Host ''
    & $make -C $repo -j $Jobs @MakeArgs
}

$code = $LASTEXITCODE
Write-Host ''
if ($code -eq 0) {
    Write-Host "build OK (exit 0)" -ForegroundColor Green
    $exe = Join-Path $repo 'bin\codol_dedrun.exe'
    if (Test-Path $exe) {
        $f = Get-Item $exe
        Write-Host ("  {0}  {1:N0} bytes  {2}" -f $f.Name, $f.Length, $f.LastWriteTime)
        Write-Host "  not promoted to codol_dedrun_next.exe -- do that yourself when you want it live."
    }
} else {
    Write-Host "build FAILED (exit $code)" -ForegroundColor Red
    Write-Host "  If it failed at the LINK stage, bin\codol_dedrun.exe has been removed by ld."
    Write-Host "  bin\rollback\ holds previous builds; codol_dedrun_next.exe is untouched."
}
exit $code
