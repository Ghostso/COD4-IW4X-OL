"""Inject the CORRECTED TCLS container into a suspended game process.

Uses Hubble's corrected layout (_tenproxy_build.build) instead of the earlier
model, which put the channel-table pointer at mapped+0x4C.  The consumer
(TenProxy.dll 0x1000638C/0x10006392) actually reads mapped+0x50, so the first
attempt always handed the game zeros and ApplySettings rejected it.

Sequence:
    CreateProcess(CREATE_SUSPENDED)
    build the container bytes
    CreateFileMappingW("TCLS_SHAREDMEMEMORY<pid>", 0x80000, PAGE_READWRITE)
    MapViewOfFile -> memcpy the container
    KEEP the mapping alive (the game only opens it, never creates it)
    ResumeThread, then sample the config block / state globals

READ-ONLY w.r.t. the game itself (no WriteProcessMemory).  The only object
created is a named section the game is looking for.  ASCII only.
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import sys
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
adv = ctypes.WinDLL("advapi32", use_last_error=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SUB = os.path.join(ROOT, "CODOLServer", "_subagents")
sys.path.insert(0, SUB)
import _tenproxy_build as TB  # noqa: E402


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
    k32.CreateFileMappingW.restype = wt.HANDLE
    k32.CreateFileMappingW.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD,
                                       wt.DWORD, wt.DWORD, wt.LPCWSTR]
    k32.MapViewOfFile.restype = ctypes.c_void_p
    k32.MapViewOfFile.argtypes = [wt.HANDLE, wt.DWORD, wt.DWORD, wt.DWORD,
                                  ctypes.c_size_t]
    k32.ResumeThread.argtypes = [wt.HANDLE]
    k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]


def rd(h, va, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(va), buf, n,
                                 ctypes.byref(got)) or got.value == 0:
        return None
    return buf.raw[:got.value]


WATCH = [(0x849B61F, "B", "flag_61f"), (0x84ABA50, "I", "uA50"),
         (0x84ABA60, "I", "sub_state"), (0x84ABA5C, "I", "last_err"),
         (0x84ABB08, "I", "objA"), (0x84ABB14, "I", "objB")]
BLOCK = 0x0331C5C0
BLOCK_N = 0x40


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cwd", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float, default=90.0)
    ap.add_argument("--step", type=float, default=0.5)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=443)
    a = ap.parse_args()

    gd = os.path.abspath(a.cwd)
    exe = os.path.join(gd, "codoMP_client_shipRetail.exe")
    os.makedirs(a.out, exist_ok=True)
    lg = open(os.path.join(a.out, "inject.jsonl"), "w", encoding="utf-8")

    def ev(o):
        lg.write(json.dumps(o, ensure_ascii=False) + "\n")
        lg.flush()

    setup()
    si = SI()
    si.cb = ctypes.sizeof(si)
    pi = PI()
    buf = ctypes.create_unicode_buffer(
        '"%s" -q --disable-gpu --disable-gpu-compositing' % exe)
    ok = k32.CreateProcessW(exe, buf, None, None, True, 4, None, gd,
                            ctypes.byref(si), ctypes.byref(pi))
    ev({"ev": "create", "ok": bool(ok), "pid": pi.pid})
    if not ok:
        return 1

    # Build the corrected container and publish it under the name the game
    # will look for.  dns_text is the channel tag 8 string:
    #   "<host>;<port>;<field><field><field>" as reconstructed by Hubble.
    data = TB.build(a.host, a.port, channel=1, fields=("1004", "0", "0"),
                    dns_text=("%s;%d;1004;0;0" % (a.host, a.port)).encode())
    name = "TCLS_SHAREDMEMEMORY%d" % pi.pid
    hm = k32.CreateFileMappingW(wt.HANDLE(-1).value, None, 0x04, 0, len(data),
                                name)
    err = ctypes.get_last_error()
    ev({"ev": "mapping", "name": name, "handle": hm, "size": len(data),
        "err": err})
    if not hm:
        return 1
    p = k32.MapViewOfFile(hm, 0x000F001F, 0, 0, len(data))
    ev({"ev": "view", "ptr": p, "err": ctypes.get_last_error()})
    if not p:
        return 1
    ctypes.memmove(p, data, len(data))
    ev({"ev": "filled", "describe": TB.describe(data)})

    h = k32.OpenProcess(0x0400 | 0x0010, False, pi.pid)
    k32.ResumeThread(pi.ht)
    ev({"ev": "resumed"})
    t0 = time.time()
    while time.time() - t0 < a.seconds:
        el = round(time.time() - t0, 2)
        rec = {"t": el}
        blk = rd(h, BLOCK, BLOCK_N)
        if blk:
            dws = struct.unpack("<%dI" % (len(blk) // 4), blk)
            rec["block_head"] = [hex(x) for x in dws]
            rec["block0"] = dws[0]
        for va, fmt, nm in WATCH:
            raw = rd(h, va, struct.calcsize(fmt))
            rec[nm] = (struct.unpack(fmt, raw)[0]
                       if raw and len(raw) == struct.calcsize(fmt) else None)
        ev(rec)
        time.sleep(a.step)
    ev({"ev": "done"})
    lg.close()
    try:
        k32.TerminateProcess(pi.hp, 0)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
