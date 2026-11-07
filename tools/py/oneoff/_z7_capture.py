# -*- coding: utf-8 -*-
"""Launch + desktop-capture the game window until it lives past the DNS
decision point (~18.5s), then inspect the frames for the lobby popup panel."""
import ctypes, ctypes.wintypes as w, json, os, socket, subprocess, threading, time

u32 = ctypes.windll.user32
g32 = ctypes.windll.gdi32
ROOT = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(ROOT, "CODOLServer", "lobby3074", "logs", "shots")

class BIH(ctypes.Structure):
    _fields_ = [("biSize", w.DWORD), ("biWidth", w.LONG), ("biHeight", w.LONG),
                ("biPlanes", w.WORD), ("biBitCount", w.WORD), ("biCompression", w.DWORD),
                ("biSizeImage", w.DWORD), ("biXPelsPerMeter", w.LONG),
                ("biYPelsPerMeter", w.LONG), ("biClrUsed", w.DWORD),
                ("biClrImportant", w.DWORD)]

def game_hwnd_rect():
    r = subprocess.run(["powershell","-NoProfile","-Command",
      "Get-Process -Name codoMP_client_shipRetail -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"],
      capture_output=True)
    pids = set(int(x) for x in r.stdout.decode().split() if x.strip().isdigit())
    if not pids: return None, None
    found = [None]
    PROC = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
    def cb(h, l):
        if not u32.IsWindowVisible(h): return True
        p = w.DWORD(); u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value not in pids: return True
        cr = w.RECT(); u32.GetClientRect(h, ctypes.byref(cr))
        if (cr.right-cr.left) > 400 and (cr.bottom-cr.top) > 300:
            pt = w.POINT(0,0); u32.ClientToScreen(h, ctypes.byref(pt))
            found[0] = (pt.x, pt.y, pt.x+cr.right, pt.y+cr.bottom)
            return False
        return True
    u32.EnumWindows(PROC(cb), 0)
    return found[0], sorted(pids)

def grab(l,t,r,b):
    W,H = r-l, b-t
    if W<=0 or H<=0: return None
    hd = u32.GetDesktopWindow()
    hdc = u32.GetWindowDC(hd)
    md = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, W, H)
    g32.SelectObject(md, bmp)
    g32.BitBlt(md, 0,0,W,H, hdc, l,t, 0x00CC0020)
    bi = BIH(); bi.biSize=ctypes.sizeof(BIH); bi.biWidth=W; bi.biHeight=-H
    bi.biPlanes=1; bi.biBitCount=32; bi.biCompression=0
    buf = ctypes.create_string_buffer(W*H*4)
    g32.GetDIBits(md, bmp, 0, H, buf, ctypes.byref(bi), 0)
    g32.DeleteObject(bmp); g32.DeleteDC(md); u32.ReleaseDC(hd, hdc)
    return W,H,buf.raw

def analyse(raw, W, H):
    from PIL import Image
    im = Image.frombuffer("RGBA",(W,H),raw,"raw","BGRA",0,1).convert("RGB").resize((160,90))
    px = list(im.getdata()); n=len(px)
    blue  = sum(1 for r,g,b in px if b>100 and b>r+35 and b>g+25)
    dark  = sum(1 for r,g,b in px if r<70 and g<70 and b<90)
    white = sum(1 for r,g,b in px if r>200 and g>200 and b>200)
    return blue/n, dark/n, white/n

def agent_run(argv, timeout=900):
    st = json.load(open(os.path.join(ROOT,"CODOLServer","logs","elevated_agent.json"), encoding="utf-8"))
    req = {"action":"run","argv":argv,"token":st["token"]}
    s = socket.create_connection(("127.0.0.1", int(st["port"])), timeout=timeout)
    s.sendall((json.dumps(req)+"\n").encode("utf-8"))
    b=b""
    while not b.endswith(b"\n"):
        c=s.recv(65536)
        if not c: break
        b+=c
    return json.loads(b.decode("utf-8"))

def main():
    os.makedirs(SHOTS, exist_ok=True)
    tag = time.strftime("%Y%m%d_%H%M%S")
    logp = os.path.join(SHOTS, "watch_%s.log" % tag)
    fh = open(logp,"w",encoding="utf-8")
    def log(m):
        line="%.2f %s"%(time.time(),m); print(line,flush=True); fh.write(line+"\n"); fh.flush()

    LD = os.path.abspath(os.path.join("CODOLServer","logs","Z7_3074"))
    argv = ["powershell","-NoProfile","-ExecutionPolicy","Bypass","-File",
        os.path.join("run_codol_001","elevated_ifs1_observer.ps1"),
        "-DurationSeconds","200",
        "-Sandbox", os.path.abspath(os.path.join("run_codol_001","sandbox_ifs1_20260923")),
        "-TenProxyShm", os.path.abspath(os.path.join("CODOLServer","_subagents","_tenproxy_shm_fixed.bin")),
        "-PokeLobbyHost","127.0.0.1","-PokeLobbyPort","8443",
        "-PokeLobbyGlobals","1","-LobbyReadyOnly","1","-Post83Trace","1","-Post83Seconds","120",
        "-HandshakeReadyFile", os.path.join(LD,"ready.flag"),
        "-HandshakeEchoFile", os.path.join(LD,"echo.txt")]
    res={}
    def launch(): res["r"] = agent_run(argv)
    th = threading.Thread(target=launch, daemon=True); th.start()

    t0=time.time(); frames=[]; best=None
    while th.is_alive() and time.time()-t0 < 230:
        rc, pids = game_hwnd_rect()
        if rc:
            g = grab(*rc)
            if g:
                W,H,raw = g
                bf,df,wf = analyse(raw,W,H)
                el = time.time()-t0
                png = os.path.join(SHOTS, "%s_t%03d.png"%(tag,int(el)))
                try:
                    from PIL import Image
                    Image.frombuffer("RGBA",(W,H),raw,"raw","BGRA",0,1).convert("RGB").save(png)
                except Exception: pass
                log("t=%5.1f %dx%d blue=%.3f dark=%.3f white=%.3f pids=%s" % (el,W,H,bf,df,wf,pids))
                frames.append((el,bf,df,wf,png))
                if bf > 0.15:
                    log("  *** BLUE PANEL blue=%.3f -> %s" % (bf,png))
                    best=(el,bf,png); break
        else:
            log("no window")
        time.sleep(2.0)
    th.join(timeout=20)
    log("frames=%d" % len(frames))
    if best: log("PANEL at t=%.1f blue=%.3f %s" % best)
    else: log("no blue panel above threshold")
    log("log: %s" % logp)
    fh.close()

if __name__ == "__main__":
    main()
