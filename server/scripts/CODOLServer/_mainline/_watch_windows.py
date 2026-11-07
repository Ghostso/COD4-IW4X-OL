import ctypes, ctypes.wintypes as wt, json, os, subprocess, sys, time

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32
EnumWindows = u32.EnumWindows
EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
GetWindowTextW = u32.GetWindowTextW
GetWindowTextLengthW = u32.GetWindowTextLengthW
GetClassNameW = u32.GetClassNameW
GetWindowThreadProcessId = u32.GetWindowThreadProcessId
IsWindowVisible = u32.IsWindowVisible

out_dir = sys.argv[1]
seconds = float(sys.argv[2]) if len(sys.argv)>2 else 90.0
os.makedirs(out_dir, exist_ok=True)
log_path = os.path.join(out_dir, "windows.jsonl")
log = open(log_path, "w", encoding="utf-8")

seen = {}

def proc_name(pid):
    h = k32.OpenProcess(0x1000, False, pid)   # QUERY_LIMITED_INFORMATION
    if not h: return "?"
    buf = ctypes.create_unicode_buffer(512)
    size = wt.DWORD(512)
    ok = k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
    k32.CloseHandle(h)
    return os.path.basename(buf.value) if ok else "?"

def child_texts(hwnd):
    res=[]
    GW_CHILD=5; GW_HWNDNEXT=2; WM_GETTEXT=0x000D
    child = u32.GetWindow(hwnd, GW_CHILD)
    while child:
        ln = GetWindowTextLengthW(child)
        if ln>0:
            b = ctypes.create_unicode_buffer(ln+1)
            u32.SendMessageW(child, WM_GETTEXT, ln+1, b)
            if b.value.strip(): res.append(b.value)
        child = u32.GetWindow(child, GW_HWNDNEXT)
    return res

def cb(hwnd, lparam):
    if not IsWindowVisible(hwnd): return True
    pid = wt.DWORD()
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    ln = GetWindowTextLengthW(hwnd)
    b = ctypes.create_unicode_buffer(ln+2)
    GetWindowTextW(hwnd, b, ln+2)
    cn = ctypes.create_unicode_buffer(256)
    GetClassNameW(hwnd, cn, 256)
    key = int(hwnd)
    title = b.value
    cls = cn.value
    kids = child_texts(hwnd)
    sig = (pid.value, cls, title, tuple(kids))
    if seen.get(key) != sig:
        seen[key] = sig
        rec = {"t": round(time.time()-t0,2), "hwnd": hex(key), "pid": pid.value,
               "proc": proc_name(pid.value), "class": cls, "title": title,
               "children": kids}
        try:
            json.dump(rec, log, ensure_ascii=False); log.write("\n"); log.flush()
        except Exception: pass
        print(json.dumps(rec, ensure_ascii=False), flush=True)
    return True

t0 = time.time()
cbp = EnumProc(cb)
print("monitor start %s for %.0fs"%(out_dir, seconds), flush=True)
while time.time()-t0 < seconds:
    u32.EnumWindows(cbp, 0)
    time.sleep(0.35)
log.close()
print("monitor done", flush=True)
