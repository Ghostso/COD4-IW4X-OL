"""Hunt, inside a live client, for the decrypted nuked zone and its AES key.

Rationale: mp_nuked_load.ff ships with its whole header encrypted, so the
static RSA path used for other maps cannot recover the key.  But the engine must
decrypt it at load time, so both the 24-byte key and the plaintext zone exist in
memory while the map loads.

This scanner reads private (heap) regions only and reports:
  * offsets where "IWffs100" appears  -> decrypted zone headers
  * offsets where a 24-byte value is followed by a 16-byte counter-looking IV
  * offsets containing the already-known sibling key (control)

Must run elevated (ACE blocks OpenProcess from a normal process), and must start
BEFORE the client so the earliest handle can be grabbed.

Usage:
  python -X utf8 hunt_nuked_key.py <outdir> <seconds> <gap_seconds>
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
MEM_IMAGE = 0x1000000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01

NEEDLES = {
    "IWffs100": b"IWffs100",
    "mp_nuked": b"mp_nuked",
    # known sibling key (control: proves we can see key material at all)
    "sibling_key": bytes.fromhex("da135e91c7981459a13ddc2aed3050ae6dd9a7ce619bb6c5"),
    "zlib_78da": b"\x78\xda",
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


def scan(h, lo, hi):
    """Return hits and coverage: name -> [(va, region_type)]."""
    hits = {k: [] for k in NEEDLES}
    attempted = ok_bytes = 0
    for b, s, state, prot, ty in regions(h, lo, hi):
        if state != MEM_COMMIT or ty == MEM_IMAGE:
            continue
        if prot & PAGE_GUARD or (prot & 0xFF) == PAGE_NOACCESS:
            continue
        p = 0
        while p < s:
            n = min(0x100000, s - p)
            attempted += n
            buf = rd(h, b + p, n)
            if buf:
                ok_bytes += n
                for k, needle in NEEDLES.items():
                    st = 0
                    while True:
                        i = buf.find(needle, st)
                        if i < 0:
                            break
                        hits[k].append((b + p + i, ty))
                        st = i + 1
                        if len(hits[k]) > 200:
                            break
                p += n
            else:
                p += 0x1000
    return hits, attempted, ok_bytes


def main():
    outdir = sys.argv[1]
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 300.0
    gap = float(sys.argv[3]) if len(sys.argv) > 3 else 12.0
    os.makedirs(outdir, exist_ok=True)
    log = open(os.path.join(outdir, "hunt.txt"), "w", encoding="utf-8")
    jf = open(os.path.join(outdir, "hunt.jsonl"), "w", encoding="utf-8")
    t0 = time.time()
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    dbg, derr = enable_debug()
    w(log, t0, "SeDebugPrivilege=%s err=%d" % (dbg, derr))

    pid = h = None
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
        hits, attempted, ok_bytes = scan(h, lo, hi)
        cov = (100.0 * ok_bytes / attempted) if attempted else 0.0
        rec = {"index": idx, "t": round(time.time() - t0, 2), "pid": pid,
               "coverage_pct": round(cov, 2),
               "hits": {k: {"count": len(v),
                            "addrs": ["0x%08X" % a for a, _ in v[:40]]}
                        for k, v in hits.items()}}
        jf.write(json.dumps(rec) + "\n")
        jf.flush()
        w(log, t0, "扫描#%d 覆盖%.1f%%  " % (idx, cov) +
          "  ".join("%s=%d" % (k, len(v)) for k, v in hits.items()))
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
