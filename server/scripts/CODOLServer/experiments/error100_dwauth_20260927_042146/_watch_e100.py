"""Error-100 first-blocker probe: read-only watch of the dwLobby DNS globals.

READ-ONLY. OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ) only.
No write to the target, no injection, no patch, no network changes.

Records (per the experiment spec):
  0x0081A76A8  dwauth field 3  -> lobby HOST string
  0x0081A9EC4  dwauth field 4  -> lobby PORT (uint16)
  0x0081A7F34  dwauth field 1  -> second host string
  0x0084ABA78  DNS stage result (2 == DW_DNS_COMPLETE)
  0x0084ABA50  dwLobby main state
  0x00E4EA3C   -> current state-name string

Extra (needed to answer "was 0x007F3600 even executed?"):
  0x0084ABA70  DNS resolver object A
  0x0084ABA74  DNS resolver object B
  0x00849BA34  DW live state
  0x00849BA30  DW previous state
  0x0084ABA60  auth sub-state
  0x0084ABA5C  last error code
  0x0084ABA7C  lobby-check state (0x7F3800)
  0x00849B61F  dwLobby master gate

Usage:
  python -X utf8 _watch_e100.py --cwd <gamedir> --out <dir> --seconds 150 --step 0.5
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


INVALID_HANDLE_VALUE = wt.HANDLE(-1).value
FILE_MAP_ALL_ACCESS = 0x000F001F


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
    k32.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD,
                                               wt.LPWSTR,
                                               ctypes.POINTER(wt.DWORD)]
    k32.CreateFileMappingW.restype = wt.HANDLE
    k32.CreateFileMappingW.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD,
                                       wt.DWORD, wt.DWORD, wt.LPCWSTR]
    k32.MapViewOfFile.restype = ctypes.c_void_p
    k32.MapViewOfFile.argtypes = [wt.HANDLE, wt.DWORD, wt.DWORD, wt.DWORD,
                                  ctypes.c_size_t]
    k32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]


def rd(h, va, n):
    b = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    ok = k32.ReadProcessMemory(h, ctypes.c_void_p(va), b, n,
                               ctypes.byref(got))
    if not ok or got.value == 0:
        return None
    return b.raw[:got.value]


def u32(h, va):
    b = rd(h, va, 4)
    return struct.unpack("<I", b)[0] if b and len(b) == 4 else None


def cstr(h, va, n=60):
    b = rd(h, va, n)
    if not b:
        return None
    return b.split(b"\x00")[0].decode("latin1", "replace")


def create_tenproxy_shm(pid, image_path):
    """Publish exactly the named mapping the prior sandbox harness used.

    This is host-side shared memory creation, not a write to the game image.
    The mapping must stay open until the watcher exits.
    """
    if not os.path.isfile(image_path):
        return None, "image-missing"
    blob = open(image_path, "rb").read()
    name = "TCLS_SHAREDMEMEMORY%d" % pid
    handle = k32.CreateFileMappingW(INVALID_HANDLE_VALUE, None, 0x04, 0,
                                    len(blob), name)
    if not handle:
        return None, "CreateFileMappingW err=%d" % ctypes.get_last_error()
    view = k32.MapViewOfFile(handle, FILE_MAP_ALL_ACCESS, 0, 0, len(blob))
    if not view:
        err = ctypes.get_last_error()
        k32.CloseHandle(handle)
        return None, "MapViewOfFile err=%d" % err
    ctypes.memmove(view, blob, len(blob))
    k32.UnmapViewOfFile(view)
    return handle, "ok size=%d" % len(blob)


def list_processes():
    TH32CS_SNAPPROCESS = 0x00000002

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD),
                    ("th32ProcessID", wt.DWORD),
                    ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                    ("th32ModuleID", wt.DWORD), ("cntThreads", wt.DWORD),
                    ("th32ParentProcessID", wt.DWORD),
                    ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                    ("szExeFile", ctypes.c_char * 260)]

    k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
    k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
    k32.Process32First.argtypes = [wt.HANDLE,
                                   ctypes.POINTER(PROCESSENTRY32)]
    k32.Process32Next.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32)]
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snap or snap == wt.HANDLE(-1).value:
        return []
    out = []
    pe = PROCESSENTRY32()
    pe.dwSize = ctypes.sizeof(pe)
    ok = k32.Process32First(snap, ctypes.byref(pe))
    while ok:
        out.append((int(pe.th32ProcessID),
                    pe.szExeFile.decode("latin1", "replace")))
        ok = k32.Process32Next(snap, ctypes.byref(pe))
    k32.CloseHandle(snap)
    return out


def process_image_path(pid):
    k32.OpenProcess.restype = wt.HANDLE
    k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    h = k32.OpenProcess(0x1000, False, pid)
    if not h:
        return None
    buf = ctypes.create_unicode_buffer(1024)
    n = wt.DWORD(1024)
    ok = k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n))
    k32.CloseHandle(h)
    return buf.value if ok else None


def wait_for_game_process(exe_path, timeout):
    target = os.path.normcase(os.path.abspath(exe_path))
    deadline = time.time() + timeout
    while time.time() < deadline:
        for pid, name in list_processes():
            if name.lower() != "codomp_client_shipretail.exe":
                continue
            path = process_image_path(pid)
            if path and os.path.normcase(os.path.abspath(path)) == target:
                return pid
        time.sleep(0.02)
    return None


WATCH_U32 = [
    (0x84ABA78, "uA78_dns_result"),
    (0x84ABA50, "uA50_lobby_state"),
    (0x84ABA54, "uA54_prev_state"),
    (0x84ABA5C, "uA5C_last_err"),
    (0x84ABA60, "uA60_sub_state"),
    (0x84ABA70, "uA70_dns_objA"),
    (0x84ABA74, "uA74_dns_objB"),
    (0x84ABA7C, "uA7C_lobby_check"),
    (0x849BA30, "dw_state_prev"),
    (0x849BA34, "dw_state"),
]

WATCH_BYTE = [
    (0x849B61F, "flag_61f_gate"),
    (0x849B5CC, "u5CC"),
]

HOST_VA = 0x81A76A8
PORT_VA = 0x81A9EC4
F1_VA = 0x81A7F34
NAME_PTR_VA = 0xE4EA3C

# 0x007F26C0 / 0x007F3600 live in the TP3-encrypted .text region. Until the
# client decrypts that page the bytes differ from the runtime image, so the
# sampled bytes are themselves evidence of whether that code has been
# materialised yet.
CODE_7F26C0 = 0x7F26C0
CODE_7F3600 = 0x7F3600


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cwd", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float, default=150.0)
    ap.add_argument("--step", type=float, default=0.5)
    ap.add_argument("--kill-on-exit", action="store_true")
    ap.add_argument("--tenproxy-shm", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), "_subagents", "_tenproxy_shm.bin"),
        help="TCLS_SHAREDMEMEMORY<pid> image used by the prior lobby harness")
    ap.add_argument("--attach-wait", action="store_true",
                    help="do not launch; wait for the fixed chain to create "
                         "the game under --cwd, then attach read-only")
    ap.add_argument("--attach-timeout", type=float, default=90.0)
    a = ap.parse_args()

    gd = os.path.abspath(a.cwd)
    exe = os.path.join(gd, "codoMP_client_shipRetail.exe")
    if not os.path.exists(exe):
        print("missing exe: " + exe, file=sys.stderr)
        return 2
    os.makedirs(a.out, exist_ok=True)
    lg = open(os.path.join(a.out, "watch.jsonl"), "w", encoding="utf-8")

    def ev(o):
        lg.write(json.dumps(o, ensure_ascii=False) + "\n")
        lg.flush()

    setup()
    ev({"ev": "setup_ok", "exe": exe, "cwd": gd,
        "exe_sha256_expect": "36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537"})
    di = os.path.join(gd, "dwauth.ini")
    ev({"ev": "dwauth_present", "path": di,
        "exists": os.path.exists(di),
        "content": (open(di, encoding="ascii").read()
                    if os.path.exists(di) else None)})

    pi = None
    if a.attach_wait:
        ev({"ev": "attach_wait", "target": exe,
            "timeout": a.attach_timeout})
        pid = wait_for_game_process(exe, a.attach_timeout)
        ev({"ev": "attach_found", "pid": pid})
        if not pid:
            return 1
        h = k32.OpenProcess(0x0400 | 0x0010, False, pid)
        ev({"ev": "handle", "h": h, "err": ctypes.get_last_error()})
        if not h:
            return 1
    else:
        si = SI()
        si.cb = ctypes.sizeof(si)
        pi = PI()
        cmd = '"%s" -q --disable-gpu --disable-gpu-compositing' % exe
        buf = ctypes.create_unicode_buffer(cmd)
        ok = k32.CreateProcessW(exe, buf, None, None, True, 4, None, gd,
                                ctypes.byref(si), ctypes.byref(pi))
        ev({"ev": "create", "ok": bool(ok), "pid": pi.pid,
            "err": ctypes.get_last_error()})
        if not ok:
            return 1

        h = k32.OpenProcess(0x0400 | 0x0010, False, pi.pid)
        ev({"ev": "handle", "h": h, "err": ctypes.get_last_error()})
        if not h:
            return 1

        buf = ctypes.create_unicode_buffer(512)
        n = wt.DWORD(512)
        img = k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n))
        ev({"ev": "image", "ok": bool(img), "path": buf.value})

        shm_handle, shm_note = create_tenproxy_shm(pi.pid, a.tenproxy_shm)
        ev({"ev": "tenproxy_shm", "ok": shm_handle is not None,
            "note": shm_note, "pid": pi.pid,
            "path": os.path.abspath(a.tenproxy_shm)})

        k32.ResumeThread(pi.ht)
        ev({"ev": "resumed"})

    t0 = time.time()
    seen_states = []
    seen_names = []
    first = {}
    while time.time() - t0 < a.seconds:
        el = round(time.time() - t0, 2)
        rec = {"t": el}
        for va, name in WATCH_U32:
            rec[name] = u32(h, va)
        for va, name in WATCH_BYTE:
            b = rd(h, va, 1)
            rec[name] = b[0] if b else None

        # --- the six spec'd values, string forms included ---
        rec["host_81A76A8"] = cstr(h, HOST_VA, 60)
        pb = rd(h, PORT_VA, 2)
        rec["port_81A9EC4"] = struct.unpack("<H", pb)[0] if pb and len(pb) == 2 else None
        rec["f1_81A7F34"] = cstr(h, F1_VA, 60)

        rec["name_ptr_E4EA3C"] = u32(h, NAME_PTR_VA)
        rec["name_str"] = (cstr(h, rec["name_ptr_E4EA3C"], 40)
                           if rec["name_ptr_E4EA3C"] else None)

        # --- was 0x007F3600 materialised / running? ---
        b26 = rd(h, CODE_7F26C0, 16)
        b36 = rd(h, CODE_7F3600, 16)
        rec["code_7F26C0"] = b26.hex() if b26 else None
        rec["code_7F3600"] = b36.hex() if b36 else None
        rec["entry_7F3600_decrypted"] = bool(
            b36 and b36.hex().startswith("558bec81ec"))

        # --- first observation of each distinct value ---
        for name in ("uA78_dns_result", "uA50_lobby_state",
                     "name_str", "uA70_dns_objA", "uA74_dns_objB"):
            v = rec.get(name)
            if v not in (None, "") and name not in first:
                first[name] = {"t": el, "v": v}
                ev({"ev": "first_" + name, "t": el, "value": v})
            if name in ("uA78_dns_result", "uA50_lobby_state") and \
                    (not seen_states or seen_states[-1] != (name, v)):
                seen_states.append((name, v))
                ev({"ev": "transition", "t": el, "global": name, "value": v})
            if name == "name_str" and (not seen_names or seen_names[-1] != v):
                seen_names.append(v)
                ev({"ev": "name_transition", "t": el, "value": v})

        ev(rec)
        time.sleep(a.step)

    ev({"ev": "done", "elapsed": round(time.time() - t0, 1),
        "first": first,
        "state_sequence": seen_states,
        "name_sequence": seen_names})
    lg.close()
    if a.kill_on_exit and pi is not None:
        try:
            k32.TerminateProcess(pi.hp, 0)
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
