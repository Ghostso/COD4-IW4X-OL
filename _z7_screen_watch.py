# -*- coding: utf-8 -*-
"""Screen-capture based watcher: grabs the actual desktop pixels in the
game window's rect (works for D3D content, unlike PrintWindow)."""
import ctypes, ctypes.wintypes as w, json, os, socket, subprocess, sys, threading, time

u32 = ctypes.windll.user32
g32 = ctypes.windll.gdi32
ROOT = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(ROOT, "CODOLServer", "lobby3074", "logs", "shots")

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", w.DWORD), ("biWidth", w.LONG), ("biHeight", w.LONG),
                ("biPlanes", w.WORD), ("biBitCount", w.WORD),
                ("biCompression", w.DWORD), ("biSizeImage", w.DWORD),
                ("biXPelsPerMeter", w.LONG), ("biYPelsPerMeter", w.LONG),
                ("biClrUsed", w.DWORD), ("biClrImportant", w.DWORD)]

def game_pids():
    r = subprocess.run(["powershell","-NoProfile","-Command",
      "Get-Process | Where-Object {$_.ProcessName -match 'codoMP_client_shipRetail'} | ForEach-Object { $_.Id }"],
      capture_output=True)
    return [int(x) for x in r.stdout.decode().split() if x.strip().isdigit()]

def game_rect():
    """Return (l,t,r,b) of the game's visible window, or None."""
    pids = set(game_pids())
    found = [None]
    PROC = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
    def cb(h, l):
        if not u32.IsWindowVisible(h): return True
        p = w.DWORD(); u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value not in pids: return True
        r = w.RECT(); u32.GetClientRect(h, ctypes.byref(r))
        if (r.right-r.left) > 400 and (r.bottom-r.top) > 300:
            pt = w.POINT(0,0)
            u32.ClientToScreen(h, ctypes.byref(pt))
            found[0] = (pt.x, pt.y, pt.x+r.right, pt.y+r.bottom)
            return False
        return True
    u32.EnumWindows(PROC(cb), 0)
    return found[0]

def grab_rect(l, t, r, b):
    W, H = r-l, b-t
    hdesk = u32.GetDesktopWindow()
    hdc = u32.GetWindowDC(hdesk)
    memdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, W, H)
    g32.SelectObject(memdc, bmp)
    g32.BitBlt(memdc, 0, 0, W, H, hdc, l, t, 0x00CC0020)  # SRCCOPY
    bi = BITMAPINFOHEADER()
    bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bi.biWidth = W; bi.biHeight = -H; bi.biPlanes = 1; bi.biBitCount = 32
    bi.biCompression = 0
    bufsz = W*H*4
    buf = ctypes.create_string_buffer(bufsz)
    g32.GetDIBits(memdc, bmp, 0, H, buf, ctypes.byref(bi), 0)
    g32.DeleteObject(bmp); g32.DeleteDC(memdc); u32.ReleaseDC(hdesk, hdc)
    return W, H, buf.raw

def stats(raw):
    n = len(raw)//4
    blue = dark = 0
    for i in range(0, len(raw), 4*97):   # sample every 97th pixel for speed
        b_, g_, r_ = raw[i], raw[i+1], raw[i+2]
        if b_>110 and b_>r_+40 and b_>g_+30: blue += 1
        if r_<60 and g_<60 and b_<80: dark += 1
    tot = len(range(0, len(raw), 4*97))
    return blue/float(tot), dark/float(tot)

def save_png(W, H, raw, path):
    from PIL import Image
    im = Image.frombuffer("RGBA", (W,H), raw, "raw", "BGRA", 0, 1)
    im.convert("RGB").save(path)

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

def main():
    dur = int(sys.argv[1]) if len(sys.argv)>1 else 150
    os.makedirs(SHOTS, exist_ok=True)
    tag = time.strftime("%Y%m%d_%H%M%S")
    logp = os.path.join(SHOTS, "screen_%s.log" % tag)
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
    res={}
    def launch(): res["r"] = agent_run(argv, timeout=dur+120)
    th = threading.Thread(target=launch, daemon=True); th.start()
    log("launched; screen capture every 2s")
    t0 = time.time(); hits = []
    while th.is_alive() and time.time()-t0 < dur+30:
        rc = game_rect()
        if rc:
            try:
                W,H,raw = grab_rect(*rc)
                png = os.path.join(SHOTS, "%s_t%03d.png" % (tag, int(time.time()-t0)))
                save_png(W,H,raw,png)
                bf, df = stats(raw)
                log("  rect=%s %dx%d blue=%.3f dark=%.3f" % (rc, W, H, bf, df))
                if bf > 0.15:
                    hits.append((time.time()-t0, bf, png))
                    log("  *** BLUE PANEL? blue=%.3f -> %s" % (bf, png))
                    break
            except Exception as e:
                log("  err: %s" % e)
        else:
            log("  no game window yet")
        time.sleep(2.0)
    th.join(timeout=20)
    log("HITS=%d" % len(hits))
    for t,bf,p in hits: log("   t=%.1f blue=%.3f %s" % (t,bf,p))
    if not hits: log("threshold not reached")
    log("log: %s" % logp)
    fh.close()
    print("log:", logp)

if __name__ == "__main__":
    main()
