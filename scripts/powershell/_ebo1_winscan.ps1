param([Parameter(Mandatory=$true)][int]$TargetPid)
$code = @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class W {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr p, EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassNameW(IntPtr h, StringBuilder sb, int n);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr SendMessageTimeoutW(IntPtr h, uint msg, IntPtr wp, StringBuilder lp, uint flags, uint timeout, out IntPtr res);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  public static string Class(IntPtr h) { var sb = new StringBuilder(128); GetClassNameW(h, sb, 128); return sb.ToString(); }
  public static string Text(IntPtr h) {
    var sb = new StringBuilder(1024); IntPtr r;
    SendMessageTimeoutW(h, 0x000D, (IntPtr)1024, sb, 0x0002, 300, out r);
    return sb.ToString();
  }
}
'@
Add-Type -TypeDefinition $code
[W]::EnumWindows({ param($h,$l)
  $wp = 0; [W]::GetWindowThreadProcessId($h, [ref]$wp) | Out-Null
  if ($wp -eq $TargetPid) {
     $cls = [W]::Class($h); $txt = [W]::Text($h)
     Write-Output ("WIN hwnd=0x{0:X} class={1} visible={2} text='{3}'" -f [int64]$h, $cls, [W]::IsWindowVisible($h), $txt)
     [W]::EnumChildWindows($h, { param($c,$l2)
        $txt2 = [W]::Text($c)
        if ($txt2 -ne '') { Write-Output ("   CHILD class={0} text='{1}'" -f [W]::Class($c), $txt2) }
        return $true
     }, [IntPtr]::Zero) | Out-Null
  }
  return $true
}, [IntPtr]::Zero) | Out-Null
