Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class Win32Gui {
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
 [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
}
"@
Add-Type -AssemblyName System.Drawing
$hwnd=[IntPtr]12520734
$r=New-Object Win32Gui+RECT
[Win32Gui]::GetWindowRect($hwnd,[ref]$r) | Out-Null
$w=$r.Right-$r.Left; $h=$r.Bottom-$r.Top
if($w -lt 10 -or $h -lt 10){ Write-Output ('BAD_RECT '+$w+'x'+$h); exit }
$bmp=New-Object System.Drawing.Bitmap($w,$h)
$g=[System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($r.Left,$r.Top,0,0,(New-Object System.Drawing.Size($w,$h)))
$bmp.Save('D:\BaiduNetdiskDownload\使命召唤OL\工具\logs\gui_error.png')
Write-Output ('SAVED '+$w+'x'+$h)
