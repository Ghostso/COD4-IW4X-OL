"""Simulate the lobby success signal by patching ONE conditional jump.

Recovered chain (all VA-verified against the runtime image):

  0x803830  get-or-create the lobby connection object at [0x8269774]
  0x803780  finish routine:
              0x803781  mov esi, [0x8269774]
              0x803789  jne 0x8037AB          ; non-null -> query state
              0x803799  mov [0x84ABA50], esi  ; null -> dw_state = 0  (popup)
              0x8037BF  call 0xB7A670         ; state query, returns 0/1/2
              0x8037D6  cmp esi, 2            ; <-- patched here
              0x8037D9  je  0x8037FA          ; 74 1f  ->  eb 1f
              0x8037E4  mov [0x84ABA50], 0    ; not 2 -> dw_state = 0 (popup)
              0x8037FA  ... mov [0x84ABA50], 5 ; success -> dw_state = 5

  dw_state == 0 (or > 5, or [0x849BA3D] != 0) is what makes
  0x7F25B0 return 4, and 0x7EF210 then pushes "@SF_UI_DW_LIVE_CONNECTING_FAILED"
  (0xDE0640) -> "无法连接大厅服务!".

Patching 74 -> EB makes the jump unconditional, so the finish routine always
takes the success path and dw_state becomes 5.  Only ONE byte in the running
process is modified; no file on disk is touched.

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

PATCH_VA = 0x008037D9       # the je opcode
PATCH_OLD = b"\x74"
PATCH_NEW = b"\xEB"


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


def wbytes(h, va, data):
    old = wt.DWORD(0)
    if not k32.VirtualProtectEx(h, ctypes.c_void_p(va), len(data), 0x40,
                                ctypes.byref(old)):
        return False, "VirtualProtectEx err=%d" % ctypes.get_last_error()
    wrote = ctypes.c_size_t(0)
    ok = k32.WriteProcessMemory(h, ctypes.c_void_p(va), data, len(data),
                                ctypes.byref(wrote))
    err = ctypes.get_last_error()
    k32.VirtualProtectEx(h, ctypes.c_void_p(va), len(data), old.value,
                         ctypes.byref(wt.DWORD(0)))
    if not ok or wrote.value != len(data):
        return False, "WriteProcessMemory err=%d wrote=%d" % (err, wrote.value)
    return True, "ok"


WATCH = [(0x849B61F, "B", "flag_61f"), (0x84ABA50, "I", "uA50"),
         (0x84ABA60, "I", "sub_state"), (0x84ABA5C, "I", "last_err"),
         (0x84ABB08, "I", "objA"), (0x84ABB14, "I", "objB"),
         (0x8269774, "I", "lobbyObj"), (0x849BA3D, "B", "harderr")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cwd", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float, default=110.0)
    ap.add_argument("--step", type=float, default=0.5)
    ap.add_argument("--patch-at", type=float, default=10.0)
    a = ap.parse_args()

    gd = os.path.abspath(a.cwd)
    exe = os.path.join(gd, "codoMP_client_shipRetail.exe")
    os.makedirs(a.out, exist_ok=True)
    lg = open(os.path.join(a.out, "patch.jsonl"), "w", encoding="utf-8")

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
    h = k32.OpenProcess(0x0400 | 0x0010 | 0x0020 | 0x0008, False, pi.pid)
    ev({"ev": "handle", "h": h, "err": ctypes.get_last_error()})
    k32.ResumeThread(pi.ht)
    ev({"ev": "resumed"})

    t0 = time.time()
    patched = False
    while time.time() - t0 < a.seconds:
        el = round(time.time() - t0, 2)
        rec = {"t": el}
        before = rd(h, PATCH_VA, 1)
        rec["codebyte"] = before.hex() if before else None
        for va, fmt, nm in WATCH:
            raw = rd(h, va, struct.calcsize(fmt))
            rec[nm] = (struct.unpack(fmt, raw)[0]
                       if raw and len(raw) == struct.calcsize(fmt) else None)
        if not patched and el >= a.patch_at:
            cur = rd(h, PATCH_VA, 1)
            if cur == PATCH_OLD:
                okw, why = wbytes(h, PATCH_VA, PATCH_NEW)
                after = rd(h, PATCH_VA, 1)
                ev({"ev": "patch", "t": el, "va": hex(PATCH_VA),
                    "old": cur.hex(), "new": PATCH_NEW.hex(),
                    "ok": okw, "why": why,
                    "verify": after.hex() if after else None})
                patched = True
            else:
                ev({"ev": "patch_skip", "t": el,
                    "reason": "byte is %s, expected %s"
                              % (cur.hex() if cur else None,
                                 PATCH_OLD.hex())})
                patched = True
        ev(rec)
        time.sleep(a.step)
    ev({"ev": "done", "patched": patched})
    lg.close()
    try:
        k32.TerminateProcess(pi.hp, 0)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
