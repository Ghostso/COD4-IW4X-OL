import argparse, ctypes, ctypes.wintypes as wt, json, os, time
import subprocess

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32
g32 = ctypes.windll.gdi32

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--seconds", type=float, default=180.0)
ap.add_argument("--shot-every", type=float, default=3.0)
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)

EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
seen = {}
log = open(os.path.join(args.out, "windows.jsonl"), "w", encoding="utf-8")

class RECT(ctypes.Structure):
    _fields_=[("L",ctypes.c_long),("T",ctypes.c_long),("R",ctypes.c_long),("B",ctypes.c_long)]

def proc_name(pid):
    h = k32.OpenProcess(0x1000, False, pid)
    if not h: return "?"
    buf = ctypes.create_unicode_buffer(1024); size = wt.DWORD(1024)
    ok = k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
    k32.CloseHandle(h)
    return os.path.basename(buf.value) if ok else "?"

def all_text(hwnd):
    GW_CHILD=5; GW_HWNDNEXT=2; WM_GETTEXT=0x000D
    res=[]
    ln=u32.GetWindowTextLengthW(hwnd)
    if ln>0:
        b=ctypes.create_unicode_buffer(ln+1); u32.GetWindowTextW(hwnd,b,ln+1)
        if b.value.strip(): res.append(b.value)
    ch=u32.GetWindow(hwnd,GW_CHILD)
    while ch:
        ln=u32.GetWindowTextLengthW(ch)
        if ln>0:
            b=ctypes.create_unicode_buffer(ln+1); u32.SendMessageW(ch,WM_GETTEXT,ln+1,b)
            if b.value.strip(): res.append(b.value)
        ch=u32.GetWindow(ch,GW_HWNDNEXT)
    return res

game_hwnds=[]

def shot(hwnd, path):
    r=RECT(); u32.GetWindowRect(hwnd, ctypes.byref(r))
    w=r.R-r.L; h=r.B-r.T
    if w<80 or h<60: return False
    hdc=u32.GetWindowDC(hwnd); mdc=g32.CreateCompatibleDC(hdc)
    bmp=g32.CreateCompatibleBitmap(hdc,w,h); g32.SelectObject(mdc,bmp)
    ok=u32.PrintWindow(hwnd,mdc,2)
    class BMI(ctypes.Structure):
        _fields_=[("biSize",wt.DWORD),("biWidth",ctypes.c_long),("biHeight",ctypes.c_long),
                  ("biPlanes",wt.WORD),("biBitCount",wt.WORD),("biCompression",wt.DWORD),
                  ("biSizeImage",wt.DWORD),("biXPelsPerMeter",ctypes.c_long),("biYPelsPerMeter",ctypes.c_long),
                  ("biClrUsed",wt.DWORD),("biClrImportant",wt.DWORD)]
    bi=BMI(); bi.biSize=ctypes.sizeof(BMI); bi.biWidth=w; bi.biHeight=-h
    bi.biPlanes=1; bi.biBitCount=32; bi.biCompression=0
    bufsz=w*h*4
    buf=ctypes.create_string_buffer(bufsz)
    lines=g32.GetDIBits(mdc,bmp,0,h,buf,ctypes.byref(bi),0)
    if lines==0: return False
    hdr=(b"BM"+ (bufsz+54).to_bytes(4,"little")+ b"\x00\x00\x00\x00"+(54).to_bytes(4,"little")+
         (40).to_bytes(4,"little")+w.to_bytes(4,"little")+h.to_bytes(4,"little")+
         (1).to_bytes(2,"little")+(32).to_bytes(2,"little")+(0).to_bytes(4,"little")+
         bufsz.to_bytes(4,"little")+b"\x00"*16)
    with open(path,"wb") as f: f.write(hdr); f.write(buf.raw)
    g32.DeleteObject(bmp); g32.DeleteDC(mdc); u32.ReleaseDC(hwnd,hdc)
    return True

def cb(hwnd, lparam):
    if not u32.IsWindowVisible(hwnd): return True
    pid=wt.DWORD(); u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    t=all_text(hwnd)
    cn=ctypes.create_unicode_buffer(256); u32.GetClassNameW(hwnd,cn,256)
    key=int(hwnd); sig=(pid.value, cn.value, tuple(t))
    if key not in game_hwnds and pid.value: game_hwnds.append(key)
    if seen.get(key)!=sig:
        seen[key]=sig
        rec={"t":round(time.time()-t0,2),"hwnd":hex(key),"pid":pid.value,"proc":proc_name(pid.value),
             "class":cn.value,"texts":t}
        json.dump(rec,log,ensure_ascii=False); log.write("\n"); log.flush()
        print(json.dumps(rec,ensure_ascii=False),flush=True)
    return True

t0=time.time(); cbp=EnumProc(cb); last_shot=0
print("watch start out=%s seconds=%.0f"%(args.out,args.seconds),flush=True)
while time.time()-t0<args.seconds:
    u32.EnumWindows(cbp,0)
    now=time.time()
    if now-last_shot>=args.shot_every:
        last_shot=now
        n=0
        for h in list(game_hwnds):
            if u32.IsWindowVisible(h):
                p=os.path.join(args.out,"shot_%05.1f_%d.png"%(now-t0,h))
                try:
                    if shot(h,p): n+=1
                except Exception as e: pass
        if n: print("  shots=%d t=%.1f"%(n,now-t0),flush=True)
    time.sleep(0.4)
log.close()
print("watch done",flush=True)
