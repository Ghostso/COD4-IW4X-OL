"""Force the TCLS-derived switch [0x331C5C0] to 1 and watch what changes.

0x7F2B90 builds the *real* lobby connection object (objA) only when
[0x331C5C0] != 0; with the switch at 0 the client takes the objB fallback and
never issues POST /auth/ at all, which is exactly what every run shows.
0x641600 (ApplySettings) writes that dword from TCLS shared memory and leaves
it 0 when the TCLS data is absent.

This writes ONE dword, in the running process only:
    OpenProcess(PROCESS_VM_WRITE|PROCESS_VM_OPERATION|PROCESS_QUERY_INFORMATION)
    VirtualProtectEx -> WriteProcessMemory([0x331C5C0] = 1) -> restore
No file on disk is touched.  Still an active-memory edit, so ACE may react.

ASCII only.
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

SWITCH = 0x0331C5C0


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
    k32.WriteProcessMemory.restype = wt.BOOL
    k32.WriteProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p,
                                       ctypes.c_void_p, ctypes.c_size_t,
                                       ctypes.POINTER(ctypes.c_size_t)]
    k32.VirtualProtectEx.restype = wt.BOOL
    k32.VirtualProtectEx.argtypes = [wt.HANDLE, ctypes.c_void_p,
                                     ctypes.c_size_t, wt.DWORD,
                                     ctypes.POINTER(wt.DWORD)]
    k32.ResumeThread.argtypes = [wt.HANDLE]
    k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]


def rd(h, va, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(va), buf, n,
                                 ctypes.byref(got)) or got.value == 0:
        return None
    return buf.raw[:got.value]


def d32(h, va):
    b = rd(h, va, 4)
    return struct.unpack("I", b)[0] if b and len(b) == 4 else None


def w32(h, va, val):
    old = wt.DWORD(0)
    if not k32.VirtualProtectEx(h, ctypes.c_void_p(va), 4, 0x40,
                                ctypes.byref(old)):
        return False, "VirtualProtectEx failed err=%d" % ctypes.get_last_error()
    buf = struct.pack("<I", val)
    wrote = ctypes.c_size_t(0)
    ok = k32.WriteProcessMemory(h, ctypes.c_void_p(va), buf, 4,
                                ctypes.byref(wrote))
    err = ctypes.get_last_error()
    k32.VirtualProtectEx(h, ctypes.c_void_p(va), 4, old.value,
                         ctypes.byref(wt.DWORD(0)))
    if not ok or wrote.value != 4:
        return False, "WriteProcessMemory failed err=%d wrote=%d" % (err,
                                                                     wrote.value)
    return True, "ok"


WATCH = [(0x849B61F, "B", "flag_61f"), (0x84ABA50, "I", "uA50"),
         (0x84ABA60, "I", "sub_state"), (0x84ABA5C, "I", "last_err"),
         (0x84ABB08, "I", "objA"), (0x84ABB14, "I", "objB"),
         (0x84ABA78, "I", "uA78")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cwd", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float, default=80.0)
    ap.add_argument("--step", type=float, default=0.5)
    ap.add_argument("--poke-at", type=float, default=12.0,
                    help="seconds after resume to write the switch")
    ap.add_argument("--poke-window", type=float, default=0.0,
                    help="if >0, keep re-writing for this many seconds "
                         "(ApplySettings re-zeroes the dword every few "
                         "seconds, so a single poke gets overwritten)")
    ap.add_argument("--value", type=lambda x: int(x, 0), default=1)
    a = ap.parse_args()

    gd = os.path.abspath(a.cwd)
    exe = os.path.join(gd, "codoMP_client_shipRetail.exe")
    os.makedirs(a.out, exist_ok=True)
    lg = open(os.path.join(a.out, "poke.jsonl"), "w", encoding="utf-8")

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
    # full access so the write is possible even after ACE arms
    h = k32.OpenProcess(0x0400 | 0x0010 | 0x0020 | 0x0008, False, pi.pid)
    ev({"ev": "handle", "h": h, "err": ctypes.get_last_error()})
    if not h:
        return 1
    k32.ResumeThread(pi.ht)
    ev({"ev": "resumed"})

    t0 = time.time()
    poked = 0
    first_poke = False
    while time.time() - t0 < a.seconds:
        el = round(time.time() - t0, 2)
        rec = {"t": el, "switch": d32(h, SWITCH)}
        for va, fmt, name in WATCH:
            b = rd(h, va, struct.calcsize(fmt))
            rec[name] = (struct.unpack(fmt, b)[0]
                         if b and len(b) == struct.calcsize(fmt) else None)
        # A single write is undone by ApplySettings within ~2 s, so hold the
        # value down across the whole window that matters.
        in_window = (el >= a.poke_at
                     and (a.poke_window <= 0
                          or el <= a.poke_at + a.poke_window))
        if in_window:
            before = d32(h, SWITCH)
            okw, why = w32(h, SWITCH, a.value)
            after = d32(h, SWITCH)
            poked += 1
            if not first_poke or after != a.value:
                ev({"ev": "poke", "t": el, "before": before,
                    "value": a.value, "ok": okw, "why": why,
                    "after": after, "n": poked})
            first_poke = True
            rec["switch"] = after
        ev(rec)
        time.sleep(a.step)
    ev({"ev": "done", "pokes": poked})
    lg.close()
    try:
        k32.TerminateProcess(pi.hp, 0)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
