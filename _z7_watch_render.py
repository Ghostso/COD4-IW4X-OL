# -*- coding: utf-8 -*-
"""Watch the GAME RENDER SURFACE for the in-game lobby popup.

The popup is a GFx/Scaleform panel the game paints inside its own window
(string key @SF_UI_DW_LIVE_CONNECTING_FAILED), NOT a Windows window. So we
capture the game window with PrintWindow and look for the blue panel.
"""
import ctypes, ctypes.wintypes as w, json, os, socket, subprocess, sys, threading, time

u32 = ctypes.windll.user32
ROOT = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(ROOT, "CODOLServer", "lobby3074", "logs", "shots")

def game_pids():
    r = subprocess.run(["powershell","-NoProfile","-Command",
      "Get-Process | Where-Object {$_.ProcessName -match 'codoMP_client_shipRetail'} | ForEach-Object { $_.Id }"],
      capture_output=True)
    return [int(x) for x in r.stdout.decode().split() if x.strip().isdigit()]

def find_game_hwnd():
    pids = set(game_pids())
    best = [0, None, ""]
    PROC = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
    def cb(h, l):
        if not u32.IsWindowVisible(h): return True
        p = w.DWORD(); u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value not in pids: return True
        r = w.RECT(); u32.GetClientRect(h, ctypes.byref(r))
        a = (r.right-r.left)*(r.bottom-r.top)
        if a > best[0]:
            b = ctypes.create_unicode_buffer(256); u32.GetClassNameW(h,b,256)
            best[0], best[1], best[2] = a, h, b.value
        return True
    u32.EnumWindows(PROC(cb), 0)
    return best[1], best[2], best[0]

GRAB_PS = r'''
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
'''

def grab(hwnd, out):
    sp = os.path.join(ROOT, "_z7_grab.ps1")
    if not os.path.isfile(sp):
        open(sp,"w",encoding="ascii",newline="\r\n").write(GRAB_PS)
    r = subprocess.run(["powershell","-NoProfile","-ExecutionPolicy","Bypass","-File",
                        sp,"-Hwnd",str(hwnd),"-Out",out], capture_output=True)
    o = r.stdout.decode("utf-8","replace").strip()
    if o and o.split()[0].isdigit(): return tuple(int(x) for x in o.split()[:2])
    return None

def analyse(png):
    from PIL import Image
    im = Image.open(png).convert("RGB").resize((160,90))
    px = list(im.getdata()); n = len(px)
    blue = sum(1 for r,g,b in px if b>110 and b>r+40 and b>g+30)
    dark = sum(1 for r,g,b in px if r<60 and g<60 and b<80)
    return blue/float(n), dark/float(n)

def agent_run(argv, timeout=600):
    st = json.load(open(os.path.join(ROOT,"CODOLServer","logs","elevated_agent.json"), encoding="utf-8"))
    req = {"action":"run","argv":argv,"token":st["token"]}
    s = socket.create_connection(("127.0.0.1",int(st["port"])),timeout=timeout)
    s.sendall((json.dumps(req)+"\n").encode("utf-8"))
    b=b""
    while not b.endswith(b"\n"):
        c=s.recv(65536)
        if not c: break
        b+=c
    return json.loads(b.decode("utf-8"))

def kill_game():
    subprocess.run(["powershell","-NoProfile","-Command",
      "Get-Process | Where-Object {$_.ProcessName -match 'codoMP_client_shipRetail|AboProbe|IIPSHostApp|TP3Helper'} | Stop-Process -Force -ErrorAction SilentlyContinue"],
      capture_output=True)

def main():
    dur = int(sys.argv[1]) if len(sys.argv)>1 else 170
    os.makedirs(SHOTS, exist_ok=True)
    tag = time.strftime("%Y%m%d_%H%M%S")
    logp = os.path.join(SHOTS, "watch_%s.log" % tag)
    fh = open(logp,"w",encoding="utf-8")
    def log(m):
        line = "%.3f %s" % (time.time(), m)
        print(line, flush=True); fh.write(line+"\n"); fh.flush()
    LD = os.path.join(ROOT,"CODOLServer","logs","Z7_3074"); os.makedirs(LD, exist_ok=True)
    argv = ["powershell","-NoProfile","-ExecutionPolicy","Bypass","-File",
        os.path.join("run_codol_001","elevated_ifs1_observer.ps1"),
        "-DurationSeconds",str(dur),
        "-Sandbox", os.path.join(ROOT,"run_codol_001","sandbox_datafix_20260929"),
        "-TenProxyShm", os.path.join(ROOT,"CODOLServer","_subagents","_tenproxy_shm_fixed.bin"),
        "-PokeLobbyHost","127.0.0.1","-PokeLobbyPort","8443",
        "-PokeE57","0x00E57A5A","-PokeLobbyGlobals","1","-LobbyReadyOnly","1",
        "-Post83Trace","1","-Post83Seconds","90",
        "-HandshakeReadyFile", os.path.join(LD,"ready.flag"),
        "-HandshakeEchoFile", os.path.join(LD,"echo.txt"),
        "-PatchDelay","42","-Patch85Pass","1"]
    res = {}
    def launch(): res["r"] = agent_run(argv, timeout=dur+120)
    th = threading.Thread(target=launch, daemon=True); th.start()
    log("launched; capturing game window every 3s -> %s" % SHOTS)
    t0 = time.time(); hits = []
    while th.is_alive() and time.time()-t0 < dur+30:
        h, cls, area = find_game_hwnd()
        if h:
            png = os.path.join(SHOTS, "%s_t%03d.png" % (tag, int(time.time()-t0)))
            sz = grab(h, png)
            try:
                bf, df = analyse(png)
                log("  hwnd=0x%X class=%-22s area=%-9d size=%s blue=%.3f dark=%.3f" % (h, cls, area, sz, bf, df))
                if bf > 0.20:
                    hits.append((time.time()-t0, bf, png))
                    log("  *** BLUE PANEL? blue=%.3f -> %s" % (bf, png))
            except Exception as e:
                log("  analyse err: %s" % e)
        if hits: break
        time.sleep(3.0)
    th.join(timeout=20)
    log("agent rc=%s" % (res.get("r") or {}).get("rc"))
    log("HITS=%d" % len(hits))
    for t,bf,p in hits: log("   t=%.1f blue=%.3f %s" % (t,bf,p))
    if not hits: log("no blue panel exceeded threshold")
    fh.close()
    print("log:", logp)
    print("shots:", SHOTS)

if __name__ == "__main__":
    main()
