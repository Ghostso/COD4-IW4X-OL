"""Launch the game suspended, inject the TCLS shared memory, then resume.

Why this is the clean path (two sub-agent reports converged on it):

  * TenProxy.dll only ever calls OpenFileMappingW/MapViewOfFile -- it never
    creates the mapping, so something outside the game must create
    "TCLS_SHAREDMEMEMORY<pid>" before WinMain's ApplySettings (0x641600) runs.
  * ApplySettings then fills the 0xD40 config block at 0x331C5C0 from that
    mapping, including the "gate" dword (0x641BC8) that decides
    real-connection (objA) vs fallback (objB) at 0x7F2BA0 / 0x7F2C64.
  * A manual poke of only the gate turned out to be necessary-but-not-
    sufficient, because it left every other field at zero.

So: create the mapping while the game is still CREATE_SUSPENDED, let the
helper stay alive to keep the mapping alive, then resume.

This helper does NOT modify the game's memory.  It only creates a named
section object the game is looking for.  ASCII only.
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import subprocess
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
    k32.OpenFileMappingW.restype = wt.HANDLE
    k32.OpenFileMappingW.argtypes = [wt.DWORD, wt.BOOL, wt.LPCWSTR]
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
BLOCK = 0x0331C5C0          # 0xD40 config block


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cwd", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float, default=90.0)
    ap.add_argument("--step", type=float, default=0.5)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=443)
    ap.add_argument("--keep", type=int, default=600)
    a = ap.parse_args()

    gd = os.path.abspath(a.cwd)
    exe = os.path.join(gd, "codoMP_client_shipRetail.exe")
    os.makedirs(a.out, exist_ok=True)
    lg = open(os.path.join(a.out, "tcls.jsonl"), "w", encoding="utf-8")

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
    h = k32.OpenProcess(0x0400 | 0x0010, False, pi.pid)
    ev({"ev": "handle", "h": h})

    # Inject the TCLS mapping while the process is still suspended, so the
    # very first OpenFileMappingW inside TenProxy already sees it.
    helper = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "..", "_subagents", "_tcls_shm_layout.py")
    cmd = [sys.executable, "-X", "utf8", os.path.abspath(helper), "create",
           "--pid", str(pi.pid), "--host", a.host, "--port", str(a.port),
           "--keep", str(a.keep)]
    ev({"ev": "shm_cmd", "cmd": cmd})
    proc = subprocess.Popen(cmd, cwd=os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    time.sleep(2.5)

    # Confirm the section really exists from our side.
    name = "TCLS_SHAREDMEMEMORY%d" % pi.pid
    hmap = k32.OpenFileMappingW(0x0004, False, name)
    ev({"ev": "shm_check", "name": name, "handle": hmap,
        "err": ctypes.get_last_error()})

    k32.ResumeThread(pi.ht)
    ev({"ev": "resumed"})
    t0 = time.time()
    while time.time() - t0 < a.seconds:
        el = round(time.time() - t0, 2)
        rec = {"t": el, "block0": None}
        b = rd(h, BLOCK, 4)
        if b and len(b) == 4:
            rec["block0"] = struct.unpack("<I", b)[0]
        for va, fmt, nm in WATCH:
            raw = rd(h, va, struct.calcsize(fmt))
            rec[nm] = (struct.unpack(fmt, raw)[0]
                       if raw and len(raw) == struct.calcsize(fmt) else None)
        ev(rec)
        time.sleep(a.step)
    ev({"ev": "done"})
    lg.close()
    try:
        proc.terminate()
    except Exception:
        pass
    try:
        k32.TerminateProcess(pi.hp, 0)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
