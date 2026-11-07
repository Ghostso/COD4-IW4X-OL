# -*- coding: utf-8 -*-
"""window_dump.py -- race the ACE window to dump the client image.

Polls for the client process at 5ms granularity and starts dumping the moment
it appears, before ACE-BASE/ACE-GAME finish arming.  Writes the standard RG
sparse container plus an index JSON.

Usage: python -X utf8 window_dump.py <out_prefix> <seconds> [exe_name]
"""
import ctypes, ctypes.wintypes as wt, json, struct, subprocess, sys, time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
READABLE = (0x02, 0x04, 0x20, 0x40, 0x80)

class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wt.DWORD), ("RegionSize", ctypes.c_size_t),
                ("State", wt.DWORD), ("Protect", wt.DWORD), ("Type", wt.DWORD)]

def find_pid(name):
    r = subprocess.run(["tasklist","/FI","IMAGENAME eq "+name,"/FO","CSV","/NH"],
                       capture_output=True, text=True, errors="replace")
    for line in r.stdout.splitlines():
        c=[x.strip('"') for x in line.split('","')]
        if c and c[0].casefold()==name.casefold():
            try: return int(c[1].replace(",",""))
            except (IndexError,ValueError): pass
    return None

def try_dump(pid, prefix):
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ, False, pid)
    if not h: return None, ctypes.get_last_error()
    hdr = ctypes.create_string_buffer(0x1000); got = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(0x400000), hdr, 0x1000, ctypes.byref(got)):
        err = ctypes.get_last_error(); k32.CloseHandle(h); return None, err
    hb = hdr.raw
    if hb[:2] != b"MZ": k32.CloseHandle(h); return None, -1
    e = struct.unpack_from("<I", hb, 0x3C)[0]
    opt = e + 24
    size = struct.unpack_from("<I", hb, opt + 56)[0]
    regions=[]; gaps=[]; data_chunks=[]
    addr = 0x400000; end = 0x400000 + size; mbi = MBI()
    while addr < end:
        if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)): break
        rb = mbi.BaseAddress or 0; rs = mbi.RegionSize or 0
        if rs == 0: break
        if mbi.State == MEM_COMMIT and (mbi.Protect & 0xFF) in READABLE and not (mbi.Protect & PAGE_GUARD):
            buf = ctypes.create_string_buffer(rs); g = ctypes.c_size_t(0)
            if k32.ReadProcessMemory(h, ctypes.c_void_p(rb), buf, rs, ctypes.byref(g)) and g.value:
                data_chunks.append((rb, buf.raw[:g.value])); regions.append({"va":rb,"size":g.value})
            else:
                gaps.append({"va":rb,"size":rs,"err":ctypes.get_last_error()})
        else:
            gaps.append({"va":rb,"size":rs,"protect":mbi.Protect,"state":mbi.State})
        addr = rb + rs
    k32.CloseHandle(h)
    if not data_chunks: return None, -2
    with open(prefix+".bin","wb") as f:
        for va,data in data_chunks:
            f.write(b"RG"+struct.pack("<II",va,len(data))+data)
    with open(prefix+".json","w",encoding="utf-8") as f:
        json.dump({"pid":pid,"base":0x400000,"size":size,
                   "regions":regions,"gaps":gaps},f,indent=1)
    return sum(len(d) for _,d in data_chunks), None

def main():
    if len(sys.argv)<3: print(__doc__); return 2
    prefix=sys.argv[1]; secs=float(sys.argv[2]); name=sys.argv[3] if len(sys.argv)>3 else "codoMP_client_shipRetail.exe"
    print("waiting for %s (%.0fs)..."%(name,secs), flush=True)
    t0=time.time(); pid=None; win=None
    while time.time()-t0 < secs:
        p=find_pid(name)
        if p:
            if pid is None:
                pid=p; win=time.time()-t0
                print("PID=%d appeared at t=%.3fs, dumping..."%(pid,win), flush=True)
            n,err=try_dump(pid,prefix)
            if n:
                print("DUMP OK at t=%.3fs: %.1f MB"%(time.time()-t0,n/1048576.0), flush=True)
                return 0
            if err is not None:
                print("  read failed err=%d at t=%.3fs"%(err,time.time()-t0), flush=True)
                return 1
        time.sleep(0.005)
    print("timeout, no dump", flush=True)
    return 1

if __name__=="__main__":
    raise SystemExit(main())
