param(
  [Parameter(Mandatory=$true)][string]$Dll,
  [int]$SecVA = 0x55000
)
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
  public delegate IntPtr GetRm();
  public static IntPtr ReadPtr(IntPtr a) { return (IntPtr)Marshal.ReadInt32(a); }
  public static uint ReadU32(IntPtr a) { return (uint)Marshal.ReadInt32(a); }
  public static string ReadAnsi(IntPtr a) { return Marshal.PtrToStringAnsi(a); }
}
'@
Add-Type -TypeDefinition $code
$h = [L]::LoadLibraryW($Dll)
if ($h -eq [IntPtr]::Zero) { Write-Output ("LOAD_FAIL err=" + [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()); exit 2 }
Write-Output ("LOAD_OK base=0x" + $h.ToInt64().ToString('X'))
$p = [L]::GetProcAddress($h, 'GetResourceManagerII')
if ($p -eq [IntPtr]::Zero) { Write-Output 'EXPORT_MISSING'; exit 3 }
$d = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($p, [L+GetRm])
$rm = $d.Invoke()
Write-Output ("GetResourceManagerII -> 0x" + $rm.ToInt64().ToString('X'))
if ($rm -ne [IntPtr]::Zero) {
    $vt = [L]::ReadPtr($rm)
    Write-Output ("  RM+0x00 vtable=0x" + $vt.ToInt64().ToString('X'))
    Write-Output ("  RM+0x04 tag=" + [L]::ReadAnsi([IntPtr]::Add($rm,4)))
    $rm2 = $d.Invoke()
    Write-Output ("  2nd call -> 0x" + $rm2.ToInt64().ToString('X') + " same=" + ($rm -eq $rm2))
    $ctr = [IntPtr]::Add($h, $SecVA + 0x1000)
    $nz = @()
    for ($i = 0; $i -lt 48; $i++) { $c = [L]::ReadU32([IntPtr]::Add($ctr, $i*4)); if ($c -ne 0) { $nz += ("slot$i=$c") } }
    Write-Output ("  vtable counters nonzero: " + ($(if ($nz.Count -eq 0) { 'none' } else { $nz -join ' ' })))
    $g = [L]::ReadU32([IntPtr]::Add($h, $SecVA + 0x10C0))
    Write-Output ("  GetResourceManagerII counter = " + $g)
}
