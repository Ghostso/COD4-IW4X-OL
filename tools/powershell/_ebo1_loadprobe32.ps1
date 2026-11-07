param([Parameter(Mandatory=$true)][string]$Dll)
$code = @'
using System;
using System.Runtime.InteropServices;
public static class L {
  [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
  public static extern IntPtr LoadLibraryW(string p);
  [DllImport("kernel32.dll", SetLastError=true)]
  public static extern IntPtr GetProcAddress(IntPtr m, string n);
  [DllImport("kernel32.dll")]
  public static extern IntPtr GetModuleHandleW(string n);
}
'@
Add-Type -TypeDefinition $code -ErrorAction SilentlyContinue
$h = [L]::LoadLibraryW($Dll)
if ($h -eq [IntPtr]::Zero) {
    $e = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
    Write-Output ("LOAD_FAIL err=" + $e)
} else {
    Write-Output ("LOAD_OK base=0x" + $h.ToInt64().ToString('X'))
    $p = [L]::GetProcAddress($h, 'GetResourceManagerII')
    Write-Output ("GetResourceManagerII=0x" + $p.ToInt64().ToString('X'))
    $p2 = [L]::GetProcAddress($h, 'GetResourceManager')
    Write-Output ("GetResourceManager=0x" + $p2.ToInt64().ToString('X'))
}
