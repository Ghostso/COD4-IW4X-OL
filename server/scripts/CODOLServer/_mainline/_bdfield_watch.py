"""Sample the BD object's HTTP sub-object and its status accessors.

0xBAA2D0 reads:
    objHttp = [objB + 0x160]
    st1 = (*(objHttp->vtbl + 0x34))(objHttp)   -> HTTP status code
    st2 = (*(objHttp->vtbl + 0x38))(objHttp)   -> BD state
    if st1 == 0 -> BD_EMPTY;  if st1 == 200 -> 0x2BC (success)

We cannot call into the process, but we CAN read the raw fields so we know
whether objB+0x160 is even populated and what its status dword holds.

READ-ONLY.  ASCII only.
Usage: python -X utf8 _bdfield_watch.py --cwd <dir> --out <dir> \
       --seconds 70 --step 0.5
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
                                 ctypes.byref(got)):
        return None
    if got.value == 0:
        return None
    return buf.raw[:got.value]


def d32(h, va):
    b = rd(h, va, 4)
    return struct.unpack("I", b)[0] if b and len(b) == 4 else None


OBJB = 0x84ABB14           # objB pointer slot
STATES = [(0x849B61F, "B", "flag_61f"), (0x84ABA50, "I", "uA50"),
          (0x84ABA60, "I", "sub_state"), (0x84ABA5C, "I", "last_err")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cwd", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float, default=70.0)
    ap.add_argument("--step", type=float, default=0.5)
    a = ap.parse_args()

    gd = os.path.abspath(a.cwd)
    exe = os.path.join(gd, "codoMP_client_shipRetail.exe")
    os.makedirs(a.out, exist_ok=True)
    lg = open(os.path.join(a.out, "bd.jsonl"), "w", encoding="utf-8")

    def ev(o):
        lg.write(json.dumps(o, ensure_ascii=False) + "\n")
        lg.flush()

    setup()
    si = SI()
    si.cb = ctypes.sizeof(si)
    pi = PI()
    cmd = '"%s" -q --disable-gpu --disable-gpu-compositing' % exe
    buf = ctypes.create_unicode_buffer(cmd)
    ok = k32.CreateProcessW(exe, buf, None, None, True, 4, None, gd,
                            ctypes.byref(si), ctypes.byref(pi))
    ev({"ev": "create", "ok": bool(ok), "pid": pi.pid})
    if not ok:
        return 1
    h = k32.OpenProcess(0x0400 | 0x0010, False, pi.pid)
    ev({"ev": "handle", "h": h})
    if not h:
        return 1
    k32.ResumeThread(pi.ht)
    ev({"ev": "resumed"})

    t0 = time.time()
    while time.time() - t0 < a.seconds:
        rec = {"t": round(time.time() - t0, 2)}
        for va, fmt, name in STATES:
            b = rd(h, va, struct.calcsize(fmt))
            rec[name] = (struct.unpack(fmt, b)[0]
                         if b and len(b) == struct.calcsize(fmt) else None)
        objB = d32(h, OBJB)
        rec["objB"] = objB
        if objB:
            rec["objB_20"] = d32(h, objB + 0x20)      # task flag
            rec["objB_156c"] = d32(h, objB + 0x156C)  # obj_code
            hobj = d32(h, objB + 0x160)               # HTTP sub-object
            rec["httpobj"] = hobj
            if hobj:
                vt = d32(h, hobj)
                rec["httpobj_vt"] = vt
                if vt:
                    # method pointers at vtbl+0x34 / +0x38
                    rec["vt_34"] = d32(h, vt + 0x34)
                    rec["vt_38"] = d32(h, vt + 0x38)
                # 0xC74FE0 (vtbl+0x38) returns [httpobj+0x444] = BD state
                # 0xC74FD0 (vtbl+0x34) returns [httpobj+0x464] = HTTP status
                # Our empty 200 must land in +0x464 for the code to reach
                # "if st1 == 200 then 0x2BC", so these two dwords are the
                # whole story.
                rec["http_444"] = d32(h, hobj + 0x444)
                rec["http_464"] = d32(h, hobj + 0x464)
                rec["http_448"] = d32(h, hobj + 0x448)
                rec["http_468"] = d32(h, hobj + 0x468)
                rec["http_04"] = d32(h, hobj + 0x04)
                rec["http_1c"] = d32(h, hobj + 0x1C)
                body = rd(h, hobj + 0x1C, 4)
                if body:
                    p = struct.unpack("<I", body)[0]
                    rec["http_1c_ptr"] = p
                    if p:
                        pb = rd(h, p, 64)
                        if pb:
                            rec["http_body_head"] = pb[:48].hex()
                # scrub the object for the status dwords the accessors return
                raw = rd(h, hobj, 0x400)
                if raw:
                    dws = struct.unpack("<%dI" % (len(raw) // 4),
                                        raw[:len(raw) // 4 * 4])
                    rec["httpobj_head"] = [hex(x) for x in dws[:16]]
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
