import json, subprocess, sys, time, ctypes, ctypes.wintypes as wt
TARGET = "codoMP_client_shipRetail.exe"
def pids():
    raw = subprocess.run(["tasklist","/FI","IMAGENAME eq "+TARGET,"/FO","CSV","/NH"],capture_output=True,text=True,errors="replace").stdout
    out=[]
    for line in raw.splitlines():
        c=[x.strip('"') for x in line.split('","')]
        if c and c[0].casefold()==TARGET.casefold():
            try: out.append(int(c[1].replace(",","")))
            except: pass
    return out
k32=ctypes.WinDLL("kernel32",use_last_error=True)
k32.OpenProcess.restype=wt.HANDLE
k32.OpenProcess.argtypes=[wt.DWORD,wt.BOOL,wt.DWORD]
k32.GetExitCodeProcess.restype=wt.BOOL
k32.GetExitCodeProcess.argtypes=[wt.HANDLE,ctypes.POINTER(wt.DWORD)]
k32.CloseHandle.restype=wt.BOOL
known={}
start=time.time()
outfile=open(sys.argv[1],"w",encoding="utf-8",buffering=1)
while time.time()-start<75:
    cur=pids()
    now=round(time.time()-start,3)
    for p in cur:
        if p not in known:
            known[p]={"first":now,"handle":None,"title":None}
            try:
                import ctypes
                user32=ctypes.WinDLL("user32")
                user32.GetWindowTextW.argtypes=[wt.HWND,wt.LPWSTR,ctypes.c_int]
                hwnd=None
                # get main window handle via process
            except: pass
            row={"t":now,"kind":"start","pid":p}; outfile.write(json.dumps(row)+"\n"); print(json.dumps(row),flush=True)
    for p in list(known):
        if p not in cur and known[p].get("handle"):
            # process gone; read exit code from stored handle
            code=wt.DWORD(0)
            h=known[p]["handle"]
            k32.GetExitCodeProcess(h,ctypes.byref(code))
            k32.CloseHandle(h)
            row={"t":now,"kind":"exit","pid":p,"code":"0x%08X"%code.value,"code_signed":code.value,"lifetime":round(now-known[p]["first"],3)}
            outfile.write(json.dumps(row)+"\n"); print(json.dumps(row),flush=True)
            del known[p]
        elif p in cur and not known[p].get("handle"):
            h=k32.OpenProcess(0x1F0FFF,False,p)
            if h: known[p]["handle"]=h
    time.sleep(0.1)
for p,v in known.items():
    h=v.get("handle")
    if h:
        code=wt.DWORD(0); k32.GetExitCodeProcess(h,ctypes.byref(code))
        row={"t":round(time.time()-start,3),"kind":"alive_at_end","pid":p,"code":"0x%08X"%code.value,"lifetime":round(time.time()-start-v["first"],3)}
        outfile.write(json.dumps(row)+"\n"); print(json.dumps(row),flush=True)
        k32.CloseHandle(h)
outfile.close()
