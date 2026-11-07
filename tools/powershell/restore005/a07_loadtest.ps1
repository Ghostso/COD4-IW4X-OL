<#
  Agent 07 — Real Windows loader test.
  Uses Add-Type (compiles a C# P/Invoke shim) then calls LoadLibraryW /
  GetProcAddress / GetLastError. This is REAL loader instrumentation, not a
  static inference.
#>
param(
    [Parameter(Mandatory=$true)][string]$Dll,
    [string[]]$Exports = @("GetResourceManagerII","ReleaseResourceManagerII"),
    [switch]$CallExports
)

$ErrorActionPreference = "Continue"
$src = @'
using System;
using System.Runtime.InteropServices;
public static class NativeLoader {
    [DllImport("kernel32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    public static extern IntPtr LoadLibraryW(string lpLibFileName);
    [DllImport("kernel32.dll", SetLastError=true, CharSet=CharSet.Ansi, EntryPoint="GetProcAddress")]
    public static extern IntPtr GetProcAddress(IntPtr hModule, string lpProcName);
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern bool FreeLibrary(IntPtr hModule);
}
'@
try {
    Add-Type -TypeDefinition $src -Language CSharp -ErrorAction Stop | Out-Null
} catch {
    Write-Output "HARNESS_BUILD = FAILED"
    Write-Output ("HARNESS_ERROR = " + $_.Exception.Message)
    exit 3
}

$full = [System.IO.Path]::GetFullPath($Dll)
Write-Output "TARGET = $full"
Write-Output ("TARGET_EXISTS = " + (Test-Path -LiteralPath $full))
Write-Output ("TARGET_SHA256 = " + (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash)
Write-Output ("LOADER_BITS = " + [IntPtr]::Size * 8)

$h = [NativeLoader]::LoadLibraryW($full)
$err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
if ($h -eq [IntPtr]::Zero) {
    Write-Output "LOADLIBRARY = FAIL"
    Write-Output ("GETLASTERROR = " + $err)
    try {
        $msg = (New-Object System.ComponentModel.Win32Exception($err)).Message
    } catch { $msg = "(unavailable)" }
    Write-Output ("ERROR_MESSAGE = " + $msg)
    exit 1
}

Write-Output "LOADLIBRARY = PASS"
Write-Output ("MODULE_HANDLE = 0x{0:X}" -f [int64]$h)
Write-Output ("GETLASTERROR = " + $err)

$rc = 0
foreach ($e in $Exports) {
    $p = [NativeLoader]::GetProcAddress($h, $e)
    $e2 = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
    if ($p -eq [IntPtr]::Zero) {
        Write-Output ("GETPROCADDRESS[$e] = FAIL  err=$e2")
        $rc = 2
    } else {
        Write-Output ("GETPROCADDRESS[$e] = PASS  addr=0x{0:X}" -f [int64]$p)
    }
}

if ($CallExports) {
    foreach ($e in $Exports) {
        $p = [NativeLoader]::GetProcAddress($h, $e)
        if ($p -ne [IntPtr]::Zero) {
            try {
                $del = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer(
                    $p, [Type]([Func[Int32]]))
                $r = $del.Invoke()
                Write-Output ("CALL[$e] = OK  ret=0x{0:X}" -f [int64]$r)
            } catch {
                Write-Output ("CALL[$e] = EXCEPTION  " + $_.Exception.Message)
                $rc = 4
            }
        }
    }
}

[NativeLoader]::FreeLibrary($h) | Out-Null
exit $rc
