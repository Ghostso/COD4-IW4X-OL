"""M1 targeted scanner: count heap instances of known vtables, repeatedly.

Why not full snapshots: the question is only "do these vtables have heap
instances", so read private (heap) regions only and search for the 4-byte
vtable pointers. Output stays tiny; runs for the whole session.

Must run elevated (ACE blocks OpenProcess from a normal process: err=5),
and must start BEFORE the client so the earliest handle can be grabbed.

Usage:
  python -X utf8 m1_scan_vtables.py <outdir> <seconds> <gap_seconds>
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import sys
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

TARGET = "codoMP_client_shipRetail.exe"
PROC_ALL = 0x0008 | 0x0010 | 0x0020 | 0x0400
MEM_COMMIT = 0x1000
MEM_PRIVATE = 0x20000
MEM_IMAGE = 0x1000000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01

# vtables (VA; image is at fixed base 0x00400000)
VT = {
    "my_event_handler": 0x00DC78F0,   # MyEventHandler  (question 4)
    "dwroommatchuber": 0x00DC795C,    # positive control
    "dwroomimp": 0x00DC7274,          # positive control 2
    "dwroommessage_text": 0x00DC7504, # unrelated control (Text handler)
}
# globals worth reading alongside
GLOBALS = {
    "dwRoomMatchUber_obj": 0x082E1518,   # [0x82E1518]
    "start_requested": 0x0849B61C,       # [0x849B61C]
    "conn_obj": 0x08269774,              # [0x8269774]
}

k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                               ctypes.c_size_t]
k32.CloseHandle.argtypes = [wt.HANDLE]


class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p),
                ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wt.DWORD),
                ("PartitionId", wt.DWORD),
                ("RegionSize", ctypes.c_size_t),
                ("State", wt.DWORD), ("Protect", wt.DWORD), ("Type", wt.DWORD)]


class PE32(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD),
                ("th32ProcessID", wt.DWORD),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wt.DWORD), ("cntThreads", wt.DWORD),
                ("th32ParentProcessID", wt.DWORD),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                ("szExeFile", ctypes.c_char * 260)]


def enable_debug():
    advapi32.OpenProcessToken.argtypes = [wt.HANDLE, wt.DWORD,
                                          ctypes.POINTER(wt.HANDLE)]
    advapi32.OpenProcessToken.restype = wt.BOOL
    advapi32.LookupPrivilegeValueW.argtypes = [wt.LPCWSTR, wt.LPCWSTR,
                                               ctypes.POINTER(ctypes.c_int64)]
    advapi32.AdjustTokenPrivileges.argtypes = [wt.HANDLE, wt.BOOL, ctypes.c_void_p,
                                               wt.DWORD, ctypes.c_void_p,
                                               ctypes.c_void_p]
    htok = wt.HANDLE()
    if not advapi32.OpenProcessToken(k32.GetCurrentProcess(), 0x0020 | 0x0008,
                                     ctypes.byref(htok)):
        return False, ctypes.get_last_error()
    luid = ctypes.c_int64()
    if not advapi32.LookupPrivilegeValueW(None, "SeDebugPrivilege",
                                          ctypes.byref(luid)):
        return False, ctypes.get_last_error()

    class LAA(ctypes.Structure):
        _fields_ = [("Luid", ctypes.c_int64), ("Attr", wt.DWORD)]

    class TP(ctypes.Structure):
        _fields_ = [("n", wt.DWORD), ("p", LAA * 1)]

    tp = TP(1, (LAA * 1)(LAA(luid.value, 0x00000002)))
    ok = advapi32.AdjustTokenPrivileges(htok, False, ctypes.byref(tp), 0, None, None)
    return bool(ok), ctypes.get_last_error()


def find_pid(name):
    k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
    h = k32.CreateToolhelp32Snapshot(0x00000002, 0)
    if not h:
        return None
    pe = PE32()
    pe.dwSize = ctypes.sizeof(PE32)
    ok = k32.Process32First(h, ctypes.byref(pe))
    found = None
    while ok:
        if pe.szExeFile.decode(errors="replace").casefold() == name.casefold():
            found = pe.th32ProcessID
            break
        ok = k32.Process32Next(h, ctypes.byref(pe))
    k32.CloseHandle(h)
    return found


def rd(h, addr, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, n,
                                 ctypes.byref(got)) or got.value != n:
        return None
    return buf.raw


def regions(h, lo, hi):
    out = []
    addr = lo
    mbi = MBI()
    while addr < hi:
        if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr),
                                  ctypes.byref(mbi), ctypes.sizeof(mbi)):
            break
        b = mbi.BaseAddress or 0
        s = mbi.RegionSize or 0
        if s == 0:
            break
        out.append((b, s, int(mbi.State), int(mbi.Protect), int(mbi.Type)))
        nxt = b + s
        if nxt <= addr:
            break
        addr = nxt
    return out


def w(log, t0, msg):
    line = "[%8.3fs] %s" % (time.time() - t0, msg)
    print(line, flush=True)
    log.write(line + "\n")
    log.flush()


def scan(h, patterns, lo, hi):
    """Return ({name: [(addr, region_type), ...]}, attempted, read_bytes)."""
    hits = {k: [] for k in patterns}
    pat = {k: struct.pack("<I", v) for k, v in patterns.items()}
    attempted = 0
    ok_bytes = 0
    for b, s, state, prot, ty in regions(h, lo, hi):
        if state != MEM_COMMIT:
            continue
        if ty == MEM_IMAGE:
            continue                      # vtables live in the image; instances in heap
        if prot & PAGE_GUARD or (prot & 0xFF) == PAGE_NOACCESS:
            continue
        p = 0
        while p < s:
            n = min(0x100000, s - p)
            attempted += n
            buf = rd(h, b + p, n)
            if buf:
                ok_bytes += n
                for k, needle in pat.items():
                    start = 0
                    while True:
                        i = buf.find(needle, start)
                        if i < 0:
                            break
                        hits[k].append((b + p + i, ty))
                        start = i + 1
                p += n
            else:
                p += 0x1000
    return hits, attempted, ok_bytes


def main():
    outdir = sys.argv[1]
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 300.0
    gap = float(sys.argv[3]) if len(sys.argv) > 3 else 20.0
    os.makedirs(outdir, exist_ok=True)
    logp = os.path.join(outdir, "scan.txt")
    jsonp = os.path.join(outdir, "scan.jsonl")
    log = open(logp, "w", encoding="utf-8")
    jf = open(jsonp, "w", encoding="utf-8")
    t0 = time.time()
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    dbg, derr = enable_debug()
    w(log, t0, "SeDebugPrivilege=%s err=%d" % (dbg, derr))

    pid = None
    h = None
    while time.time() - t0 < 600:
        p = find_pid(TARGET)
        if p is not None:
            pid = p
            h = k32.OpenProcess(PROC_ALL, False, pid)
            if h:
                w(log, t0, "★ 句柄到手 pid=%d handle=0x%X" % (pid, h))
                break
        time.sleep(0.005)
    if not h:
        w(log, t0, "拿不到句柄")
        return 2

    first = rd(h, 0x00400000, 4)
    w(log, t0, "首读 0x00400000 = %s" % (first.hex() if first else
                                         "失败 err=%d" % ctypes.get_last_error()))

    lo, hi = 0x00010000, 0x7FFF0000
    idx = 0
    while time.time() - t0 < secs:
        idx += 1
        hits, attempted, ok_bytes = scan(h, VT, lo, hi)
        gl = {}
        for name, addr in GLOBALS.items():
            d = rd(h, addr, 4)
            gl[name] = ("0x%08X" % struct.unpack("<I", d)[0]) if d else None
        cov = (100.0 * ok_bytes / attempted) if attempted else 0.0
        rec = {
            "index": idx, "t": round(time.time() - t0, 2), "pid": pid,
            "coverage_pct": round(cov, 2),
            "private_bytes": attempted, "private_read_bytes": ok_bytes,
            "vtable_hits": {k: {"count": len(v), "addrs": ["0x%08X" % a for a, _ in v[:20]]}
                            for k, v in hits.items()},
            "globals": gl,
        }
        jf.write(json.dumps(rec) + "\n")
        jf.flush()
        w(log, t0, "扫描#%d 覆盖%.1f%%  " % (idx, cov) + "  ".join(
            "%s=%d" % (k, len(v)) for k, v in hits.items()) +
          "  " + " ".join("%s=%s" % (k, v) for k, v in gl.items()))
        if time.time() - t0 >= secs:
            break
        time.sleep(gap)
    w(log, t0, "结束，共 %d 轮" % idx)
    k32.CloseHandle(h)
    log.close()
    jf.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
