"""Scan the game's heap for every HTTP-object instance (vtbl 0xD95600).

_bdfield_watch proved [objB+0x160] never gets its status code written, so the
reply we send is being consumed by a DIFFERENT HTTP object.  This finds all of
them so we can see which one actually carries the BD exchange.

READ-ONLY.  ASCII only.
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import sys
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
adv = ctypes.WinDLL("advapi32", use_last_error=True)


class LUID(ctypes.Structure):
    _fields_ = [("L", wt.DWORD), ("H", wt.LONG)]


class LAA(ctypes.Structure):
    _fields_ = [("Luid", LUID), ("Attr", wt.DWORD)]


class TP(ctypes.Structure):
    _fields_ = [("n", wt.DWORD), ("p", LAA * 1)]


class SI(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("r", wt.LPWSTR), ("d", wt.LPWSTR),
                ("t", wt.LPWSTR), ("x", wt.DWORD), ("y", wt.DWORD),
                ("xs", wt.DWORD), ("ys", wt.DWORD), ("xc", wt.DWORD),
                ("yc", wt.DWORD), ("fa", wt.DWORD), ("fl", wt.DWORD),
                ("sw", wt.WORD), ("cr", wt.WORD), ("rp", ctypes.c_void_p),
                ("hi", wt.HANDLE), ("ho", wt.HANDLE), ("he", wt.HANDLE)]


class PI(ctypes.Structure):
    _fields_ = [("hp", wt.HANDLE), ("ht", wt.HANDLE),
                ("pid", wt.DWORD), ("tid", wt.DWORD)]


class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase",
                                                   ctypes.c_void_p),
                ("AllocationProtect", wt.DWORD), ("RegionSize",
                                                  ctypes.c_size_t),
                ("State", wt.DWORD), ("Protect", wt.DWORD),
                ("Type", wt.DWORD)]


VTBL = 0x00D95600          # the HTTP object vtable seen at objB+0x160


def setup():
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    adv.OpenProcessToken.argtypes = [ctypes.c_void_p, wt.DWORD,
                                     ctypes.POINTER(ctypes.c_void_p)]
    adv.LookupPrivilegeValueW.argtypes = [wt.LPCWSTR, wt.LPCWSTR,
                                          ctypes.POINTER(LUID)]
    adv.AdjustTokenPrivileges.argtypes = [ctypes.c_void_p, wt.BOOL,
                                          ctypes.POINTER(TP), wt.DWORD,
                                          ctypes.c_void_p,
                                          ctypes.POINTER(wt.DWORD)]
    h = ctypes.c_void_p()
    adv.OpenProcessToken(k32.GetCurrentProcess(), 0x28, ctypes.byref(h))
    lu = LUID()
    adv.LookupPrivilegeValueW(None, "SeDebugPrivilege", ctypes.byref(lu))
    tp = TP()
    tp.n = 1
    tp.p[0].Luid = lu
    tp.p[0].Attr = 2
    adv.AdjustTokenPrivileges(h, False, ctypes.byref(tp), 0, None, None)
    k32.CreateProcessW.restype = wt.BOOL
    k32.CreateProcessW.argtypes = [
        wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wt.BOOL,
        wt.DWORD, ctypes.c_void_p, wt.LPCWSTR, ctypes.POINTER(SI),
        ctypes.POINTER(PI)]
    k32.OpenProcess.restype = wt.HANDLE
    k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    k32.ReadProcessMemory.restype = wt.BOOL
    k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p,
                                      ctypes.c_void_p, ctypes.c_size_t,
                                      ctypes.POINTER(ctypes.c_size_t)]
    k32.VirtualQueryEx.restype = ctypes.c_size_t
    k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p,
                                   ctypes.POINTER(MBI), ctypes.c_size_t]
    k32.ResumeThread.argtypes = [wt.HANDLE]
    k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]


def rd(h, va, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(va), buf, n,
                                 ctypes.byref(got)):
        return None
    return buf.raw[:got.value] if got.value else None


def regions(h):
    addr = 0x00010000
    maxaddr = 0x7FFF0000
    mbi = MBI()
    out = []
    while addr < maxaddr:
        if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr),
                                  ctypes.byref(mbi), ctypes.sizeof(mbi)):
            break
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize
        if (mbi.State == 0x1000 and size and size <= 0x4000000
                and (mbi.Protect & 0xFF) in (0x02, 0x04, 0x40, 0x20)):
            out.append((base, size))
        addr = base + size
        if size == 0:
            addr += 0x1000
    return out


def scan(h):
    needle = struct.pack("<I", VTBL)
    hits = []
    for base, size in regions(h):
        data = rd(h, base, size)
        if not data:
            continue
        start = 0
        while True:
            i = data.find(needle, start)
            if i < 0:
                break
            # vtbl sits at offset 0 of the object, so the object starts at
            # base+i and the interesting fields follow it.
            obj = base + i
            tail = data[i:i + 0x480]
            if len(tail) >= 0x468:
                h04 = struct.unpack_from("<I", tail, 0x04)[0]
                h444 = struct.unpack_from("<I", tail, 0x444)[0]
                h464 = struct.unpack_from("<I", tail, 0x464)[0]
                hits.append({"obj": obj, "f04": h04, "f444": h444,
                             "f464": h464})
            start = i + 4
    return hits


def main():
    cwd = sys.argv[1]
    outdir = sys.argv[2]
    secs = float(sys.argv[3]) if len(sys.argv) > 3 else 60.0
    gd = os.path.abspath(cwd)
    os.makedirs(outdir, exist_ok=True)
    lg = open(os.path.join(outdir, "scan.jsonl"), "w", encoding="utf-8")

    setup()
    exe = os.path.join(gd, "codoMP_client_shipRetail.exe")
    si = SI()
    si.cb = ctypes.sizeof(si)
    pi = PI()
    buf = ctypes.create_unicode_buffer(
        '"%s" -q --disable-gpu --disable-gpu-compositing' % exe)
    ok = k32.CreateProcessW(exe, buf, None, None, True, 4, None, gd,
                            ctypes.byref(si), ctypes.byref(pi))
    lg.write(json.dumps({"ev": "create", "ok": bool(ok),
                         "pid": pi.pid}) + "\n")
    lg.flush()
    if not ok:
        return 1
    h = k32.OpenProcess(0x0400 | 0x0010, False, pi.pid)
    k32.ResumeThread(pi.ht)

    t0 = time.time()
    while time.time() - t0 < secs:
        try:
            hits = scan(h)
        except Exception as e:
            hits = []
        rec = {"t": round(time.time() - t0, 2), "n": len(hits),
               "hits": [{"obj": hex(x["obj"]), "f04": x["f04"],
                         "f444": x["f444"], "f464": x["f464"]}
                        for x in hits]}
        lg.write(json.dumps(rec) + "\n")
        lg.flush()
        time.sleep(1.5)
    lg.write(json.dumps({"ev": "done"}) + "\n")
    lg.close()
    try:
        k32.TerminateProcess(pi.hp, 0)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
