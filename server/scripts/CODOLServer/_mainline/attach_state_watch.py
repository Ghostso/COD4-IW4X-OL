"""Read-only state sampler for the real codoMP process.

Finds the sandbox game process, reads the known lobby globals, and records the
HTTP object fields without launching, writing, injecting, or patching it.
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import sys
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

TH32CS_SNAPPROCESS = 0x00000002
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010

class PE(ctypes.Structure):
    _fields_ = [("size", wt.DWORD), ("usage", wt.DWORD), ("pid", wt.DWORD),
                ("heap", ctypes.POINTER(wt.DWORD)), ("mod", wt.DWORD),
                ("threads", wt.DWORD), ("ppid", wt.DWORD), ("pri", wt.LONG),
                ("flags", wt.DWORD), ("exe", wt.WCHAR * 260)]

k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.Process32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(PE)]
k32.Process32FirstW.restype = wt.BOOL
k32.Process32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(PE)]
k32.Process32NextW.restype = wt.BOOL
k32.OpenProcess.restype = wt.HANDLE
k32.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD,
                                            wt.LPWSTR, ctypes.POINTER(wt.DWORD)]
k32.QueryFullProcessImageNameW.restype = wt.BOOL
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p,
                                  ctypes.c_void_p, ctypes.c_size_t,
                                  ctypes.POINTER(ctypes.c_size_t)]

WATCH = {
    "flag_61f": (0x849B61F, "B"), "uA50": (0x84ABA50, "I"),
    "sub_state": (0x84ABA60, "I"), "last_err": (0x84ABA5C, "I"),
    "dw_state": (0x849BA34, "I"), "uA78": (0x84ABA78, "I"),
    "objA": (0x84ABB08, "I"), "objB": (0x84ABB14, "I"),
    "objC": (0x84ABB0C, "I"),
}

def find_game():
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == wt.HANDLE(-1).value:
        return None
    p = PE(); p.size = ctypes.sizeof(PE)
    ok = k32.Process32FirstW(snap, ctypes.byref(p))
    found = None
    while ok:
        if p.exe.lower() == "codomp_client_shipretail.exe":
            found = int(p.pid); break
        ok = k32.Process32NextW(snap, ctypes.byref(p))
    k32.CloseHandle(snap)
    return found

def image_path(h):
    n = wt.DWORD(32768)
    buf = ctypes.create_unicode_buffer(n.value)
    if k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)):
        return buf.value
    return None

READ_ERRORS = 0

def read_u32(h, addr, fmt="I"):
    global READ_ERRORS
    n = struct.calcsize(fmt); b = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), b, n,
                                 ctypes.byref(got)) or got.value != n:
        READ_ERRORS += 1
        return None
    return struct.unpack("<" + fmt, b.raw)[0]

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "attach_state.jsonl"
    seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 105.0
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    t0 = time.time(); pid = None; h = None
    with open(out, "w", encoding="utf-8") as f:
        while time.time() - t0 < seconds:
            if not h:
                pid = find_game()
                if pid:
                    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
                                         False, pid)
                    rec = {"ev": "attached", "pid": pid,
                           "handle": int(h or 0),
                           "image": image_path(h) if h else None,
                           "t": round(time.time() - t0, 3)}
                    f.write(json.dumps(rec) + "\n"); f.flush()
            if h:
                rec = {"t": round(time.time() - t0, 3), "pid": pid}
                for name, (addr, fmt) in WATCH.items():
                    rec[name] = read_u32(h, addr, fmt)
                if READ_ERRORS and READ_ERRORS <= 3:
                    rec["read_error"] = ctypes.get_last_error()
                ob = rec.get("objA") or rec.get("objB")
                if ob:
                    rec["obj_code"] = read_u32(h, ob + 0x156C)
                    rec["obj_busy"] = read_u32(h, ob + 0x20)
                    rec["obj_stage"] = read_u32(h, ob + 0x14)
                    http = read_u32(h, ob + 0x160)
                    rec["httpobj"] = http
                    if http:
                        rec["http_444"] = read_u32(h, http + 0x444)
                        rec["http_464"] = read_u32(h, http + 0x464)
                        rec["http_448"] = read_u32(h, http + 0x448)
                        rec["http_468"] = read_u32(h, http + 0x468)
                        rec["http_04"] = read_u32(h, http + 0x04)
                f.write(json.dumps(rec) + "\n"); f.flush()
            time.sleep(0.2)
    return 0

if __name__ == "__main__":
    sys.exit(main())
