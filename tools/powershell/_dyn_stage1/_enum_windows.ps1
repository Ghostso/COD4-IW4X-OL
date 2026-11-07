$ErrorActionPreference='Stop'
Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class WinEnum {
 public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
 [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
 [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr hWndParent, EnumWindowsProc lpEnumFunc, IntPtr lParam);
 [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
 [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr hWnd);
 [DllImport("user32.dll")] public static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
 [DllImport("user32.dll")] public static extern IntPtr GetParent(IntPtr hWnd);
 [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
}
"@
function T([IntPtr]$h){ $n=[WinEnum]::GetWindowTextLength($h); $sb=New-Object Text.StringBuilder ($n+2); [void][WinEnum]::GetWindowText($h,$sb,$sb.Capacity); $sb.ToString() }
function C([IntPtr]$h){ $sb=New-Object Text.StringBuilder 256; [void][WinEnum]::GetClassName($h,$sb,$sb.Capacity); $sb.ToString() }
$rows=New-Object System.Collections.Generic.List[object]
$cb=[WinEnum+EnumWindowsProc]{ param($h,$l) $pidv=0; [void][WinEnum]::GetWindowThreadProcessId($h,[ref]$pidv); if($pidv -eq 20568){ $children=New-Object System.Collections.Generic.List[object]; $ccb=[WinEnum+EnumWindowsProc]{ param($ch,$cl) $cp=0; [void][WinEnum]::GetWindowThreadProcessId($ch,[ref]$cp); $items=New-Object System.Collections.Generic.List[string]; for($id=0;$id -lt 64;$id++){ $r=[WinEnum]::SendMessage($ch,0x0433,[IntPtr]$id,[IntPtr]0); if($r -ne [IntPtr]::Zero){ $items.Add(('{0}:{1}' -f $id,(T $r))) } }; $children.Add([pscustomobject]@{handle=('0x{0:X}' -f $ch.ToInt64());class=(C $ch);text=(T $ch);visible=[WinEnum]::IsWindowVisible($ch);parent=('0x{0:X}' -f ([WinEnum]::GetParent($ch)).ToInt64());items=($items -join ' | ')}) ; return $true }; [void][WinEnum]::EnumChildWindows($h,$ccb,[IntPtr]::Zero); $rows.Add([pscustomobject]@{handle=('0x{0:X}' -f $h.ToInt64());class=(C $h);text=(T $h);visible=[WinEnum]::IsWindowVisible($h);children=$children}) }; return $true }
[void][WinEnum]::EnumWindows($cb,[IntPtr]::Zero)
$rows | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath '_dyn_stage1\direct_authorized_probe\windows.json' -Encoding UTF8
Get-Content -LiteralPath '_dyn_stage1\direct_authorized_probe\windows.json'
