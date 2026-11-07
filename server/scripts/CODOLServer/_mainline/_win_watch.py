"""Launch the game exactly like the frozen chain does and DETECT popups.

The frozen chain's AboProbe log shows the interesting window as
    WINDOW_NEW,hwnd=0xC074E,class=iipsinit,text=,
i.e. the IIPS bootstrap window exists but its text is EMPTY on a healthy run.
An "初始化IIPS错误:<code>" popup means that window (or a dialog owned by it)
carries text.

This script therefore:
    * starts codoMP_client_shipRetail.exe with the SAME argv and cwd the
      frozen chain uses ('-q --disable-gpu --disable-gpu-compositing',
      cwd = sandbox_ifs1_20260923)
    * launches NOTHING else and injects NOTHING
    * polls EnumWindows for class 'iipsinit' and for dialog class '#32770',
      logging every distinct (class, text) it sees

That gives an automated pass/fail for "did a popup appear" without anyone
having to watch the screen.  ASCII only.
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

u32 = ctypes.WinDLL("user32", use_last_error=True)
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

ENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)


def windows():
    """Return [(hwnd, pid, class, text)] for top-level windows."""
    out = []

    def cb(hwnd, _):
        cls = ctypes.create_unicode_buffer(256)
        u32.GetClassNameW(hwnd, cls, 256)
        txt = ctypes.create_unicode_buffer(512)
        u32.GetWindowTextW(hwnd, txt, 512)
        pid = wt.DWORD(0)
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        out.append((int(hwnd), pid.value, cls.value, txt.value))
        return True

    u32.EnumWindows(ENUMPROC(cb), 0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cwd", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float, default=100.0)
    ap.add_argument("--step", type=float, default=0.5)
    ap.add_argument("--suspend", action="store_true",
                    help="create suspended then resume (same as the probe "
                         "scripts) instead of a plain start")
    a = ap.parse_args()

    gd = os.path.abspath(a.cwd)
    exe = os.path.join(gd, "codoMP_client_shipRetail.exe")
    os.makedirs(a.out, exist_ok=True)
    lg = open(os.path.join(a.out, "win.jsonl"), "w", encoding="utf-8")

    def ev(o):
        lg.write(json.dumps(o, ensure_ascii=False) + "\n")
        lg.flush()

    setup()
    si = SI()
    si.cb = ctypes.sizeof(si)
    pi = PI()
    buf = ctypes.create_unicode_buffer(
        '"%s" -q --disable-gpu --disable-gpu-compositing' % exe)
    flags = 4 if a.suspend else 0
    ok = k32.CreateProcessW(exe, buf, None, None, True, flags, None, gd,
                            ctypes.byref(si), ctypes.byref(pi))
    ev({"ev": "create", "ok": bool(ok), "pid": pi.pid,
        "suspended": bool(a.suspend)})
    if not ok:
        return 1
    h = None
    if a.suspend:
        h = k32.OpenProcess(0x0400 | 0x0010, False, pi.pid)
        k32.ResumeThread(pi.ht)

    t0 = time.time()
    seen = set()
    popups = []
    while time.time() - t0 < a.seconds:
        el = round(time.time() - t0, 2)
        rec = {"t": el}
        for hwnd, pid, cls, txt in windows():
            if pid != pi.pid:
                continue
            key = (cls, txt)
            if key in seen:
                continue
            seen.add(key)
            ev({"ev": "window", "t": el, "pid": pid, "class": cls,
                "text": txt})
            # A popup is any dialog, or the iipsinit window carrying text.
            if cls == "#32770" or (cls == "iipsinit" and txt.strip()):
                popups.append({"t": el, "class": cls, "text": txt})
        if h:
            for va, fmt, nm in WATCH:
                raw = rd(h, va, struct.calcsize(fmt))
                rec[nm] = (struct.unpack(fmt, raw)[0]
                           if raw and len(raw) == struct.calcsize(fmt)
                           else None)
        ev(rec)
        time.sleep(a.step)
    ev({"ev": "done", "popups": popups, "n_popups": len(popups)})
    lg.close()
    try:
        k32.TerminateProcess(pi.hp, 0)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
