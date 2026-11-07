
param([int]$Hwnd, [string]$Out)
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public class Cap2 {
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f);
  public struct RECT { public int L,T,R,B; }
  public static bool Rect(IntPtr h, out RECT r){ return GetClientRect(h, out r); }
}
"@
$r = New-Object Cap2+RECT
[Cap2]::Rect([IntPtr]$Hwnd, [ref]$r) | Out-Null
$w = $r.R-$r.L; $h = $r.B-$r.T
if ($w -le 0 -or $h -le 0) { Write-Output "BADRECT"; exit 2 }
$bmp = New-Object System.Drawing.Bitmap($w,$h)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$dc = $g.GetHdc()
[Cap2]::PrintWindow([IntPtr]$Hwnd, $dc, 2) | Out-Null
$g.ReleaseHdc($dc); $g.Dispose()
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
Write-Output "$w $h"
