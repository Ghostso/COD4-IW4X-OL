"""Launch game via the solidified chain, and capture popup timing + memory."""
import ctypes, ctypes.wintypes as wt, os, subprocess, sys, time, json

k32 = ctypes.windll.kernel32
u32 = ctypes.windll.user32
g32 = ctypes.windll.gdi32
psapi = ctypes.windll.psapi

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT  = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "_dyn_pop_out")
SECS = float(sys.argv[2]) if len(sys.argv) > 2 else 95.0
os.makedirs(OUT, exist_ok=True)
shots = os.path.join(OUT, "shots"); os.makedirs(shots, exist_ok=True)

def grab(path):
    w = u32.GetSystemMetrics(0); h = u32.GetSystemMetrics(1)
    hdc = u32.GetDC(0); mdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, h); g32.SelectObject(mdc, bmp)
    if not g32.BitBlt(mdc, 0, 0, w, h, hdc, 0, 0, 0x00CC0020): return False
    class BMI(ctypes.Structure):
        _fields_=[("biSize",wt.DWORD),("biWidth",ctypes.c_long),("biHeight",ctypes.c_long),
                  ("biPlanes",wt.WORD),("biBitCount",wt.WORD),("biCompression",wt.DWORD),
                  ("biSizeImage",wt.DWORD),("biXPelsPerMeter",ctypes.c_long),("biYPelsPerMeter",ctypes.c_long),
                  ("biClrUsed",wt.DWORD),("biClrImportant",wt.DWORD)]
    bi=BMI(); bi.biSize=ctypes.sizeof(BMI); bi.biWidth=w; bi.biHeight=-h
    bi.biPlanes=1; bi.biBitCount=24; bi.biCompression=0
    row=((w*3+3)//4)*4; bufsz=row*h
    buf=ctypes.create_string_buffer(bufsz)
    g32.GetDIBits(mdc,bmp,0,h,buf,ctypes.byref(bi),0)
    hdr=(b"BM"+(54+bufsz).to_bytes(4,"little")+b"\x00\x00\x00\x00"+(54).to_bytes(4,"little")+
         (40).to_bytes(4,"little")+w.to_bytes(4,"little")+h.to_bytes(4,"little")+
         (1).to_bytes(2,"little")+(24).to_bytes(2,"little")+(0).to_bytes(4,"little")+
         bufsz.to_bytes(4,"little")+b"\x00"*16)
    with open(path,"wb") as f: f.write(hdr); f.write(buf.raw)
    g32.DeleteObject(bmp); g32.DeleteDC(mdc); u32.ReleaseDC(0,hdc)
    return True

def game_pid():
    r = subprocess.run(['tasklist','/FI','IMAGENAME eq codoMP_client_shipRetail.exe','/FO','CSV','/NH'],
                       capture_output=True)
    t = (r.stdout or b'').decode('gbk','replace')
    for line in t.splitlines():
        parts=[x.strip('"') for x in line.split('","')]
        if len(parts)>=2 and parts[0].lower().startswith('codomp'):
            try: return int(parts[1])
            except: pass
    return None

# 启动固化链
ps = os.path.join(ROOT,'run_codol_001','capture_elevated_network.ps1')
log = open(os.path.join(OUT,'chain.stdout.txt'),'w',encoding='utf-8')
proc = subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',ps,
                         '-DurationSeconds', str(int(SECS))],
                        stdout=log, stderr=subprocess.STDOUT, cwd=ROOT)
print("chain started pid=%d"%proc.pid, flush=True)

logf = open(os.path.join(OUT,'timeline.jsonl'),'w',encoding='utf-8')
def ev(o):
    o['t']=round(time.time()-t0,2)
    logf.write(json.dumps(o,ensure_ascii=False)+'\n'); logf.flush()
    print(json.dumps(o,ensure_ascii=False),flush=True)

t0=time.time(); last_shot=0; pid=None; h=None; shotn=0
tried_open=0
while time.time()-t0 < SECS+8:
    if pid is None:
        p = game_pid()
        if p:
            pid = p
            ev({"ev":"game_found","pid":pid})
            # 尝试直接开句柄（ACE 可能拒绝）
            h = k32.OpenProcess(0x0400|0x0010, False, pid)   # QUERY|VM_READ
            ev({"ev":"openprocess","pid":pid,"handle":h,"err":ctypes.get_last_error()})
    now=time.time()
    if now-last_shot>=3.0:
        last_shot=now
        p=os.path.join(shots,"t%05.1f.bmp"%(now-t0))
        try:
            if grab(p): shotn+=1
        except Exception as e:
            ev({"ev":"shot_err","err":repr(e)})
    if pid and h and tried_open<3:
        tried_open+=1
        base=0x400000
        buf=ctypes.create_string_buffer(64)
        n=ctypes.c_size_t(0)
        ok=k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, 64, ctypes.byref(n))
        ev({"ev":"read_test","va":hex(base),"ok":bool(ok),"n":n.value,"err":ctypes.get_last_error()})
    time.sleep(0.4)

ev({"ev":"done","shots":shotn,"pid":pid})
try: proc.terminate()
except: pass
log.close(); logf.close()
