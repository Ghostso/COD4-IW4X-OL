# -*- coding: utf-8 -*-
"""
_pop3_live_dump.py - POP3 live memory evidence for the "[100] cannot connect
to lobby service" panel.

Read-only: OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ) +
ReadProcessMemory.  No injection, no patching, no network change.

The dump is taken over the current executable image of the target, whose
preferred base is 0x00400000 (confirmed with GetModuleFileNameEx at start).
It covers 0x00400000..0x00E65000, i.e. exactly the window the earlier
"full image" runs silently failed to read.

Usage:
    python -X utf8 _pop3_live_dump.py --out DIR --seconds 60 --step 2
    python -X utf8 _pop3_live_dump.py --out DIR --pid 1234 ...

Outputs in DIR:
    live.jsonl            one record per sample (+ xrefs, + new 100-dwords)
    regions.json          the committed region map inside the window
    xrefs.json            all 4-byte refs to the target strings, code vs data
    image_best.bin        densest sample
    image_t*.bin          sample at the moment the first 100-dword appears
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
psapi = ctypes.WinDLL("psapi", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01

TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002

LO = 0x00400000
HI = 0x00E65000

# both code regions of the main module (packed .text and the VM-filled gap)
CODE_RANGES = [(0x00401000, 0x00994000), (0x00994000, 0x00CA8000)]

# facts given in the brief (not re-derived here)
TARGETS = {
    "SF_UI_DW_LIVE_CONNECTING_FAILED": 0x00DE0640,
    "SF_UI_DW_LIVE_DISCONNECTED": 0x00DBD888,
    "SF_UI_DW_LIVE_CERT_FAILED": 0x00DE09F0,
    "format_bracket_pct_s": 0x00DE0768,
    "DW_LOBBY_ERROR": 0x00DE0990,
    "DW_LOBBY_CONNECTED": 0x00DE0938,
    "DW_DNS_ERROR": 0x00DE08D8,
    "DW_DNS_COMPLETE": 0x00DE08E8,
    "DW_ACCOUNT_ERROR": 0x00DE08F8,
    "DW_LOGON_ERROR": 0x00DE098C,
    "cppOnDWDisconnected": 0x00DE05E8,
    "cppOnDWConnected": 0x00DE05FC,
    "dwLogonStart": 0x00DE08C8,
    "MULTIPLE_LOGIN": 0x00DE05C0,
    "LSG_DISCONNECT_IN_GAME": 0x00DE05D0,
    "bdLobbyErrorCode": 0x00AD27F0,
    "BD_MAX_ERROR_CODE": 0x00AD27D4,
    "Unknown_bdLobbyErrorCode": 0x00AD27E8,
}


class LUID(ctypes.Structure):
    _fields_ = [("LowPart", wt.DWORD), ("HighPart", wt.LONG)]


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Luid", LUID), ("Attributes", wt.DWORD)]


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [("PrivilegeCount", wt.DWORD),
                ("Privileges", LUID_AND_ATTRIBUTES * 1)]


class MBI(ctypes.Structure):
    # 64-bit layout.  RegionSize MUST be SIZE_T; declaring it as c_size_t
    # here is what the earlier full-image tool got wrong (it produced a
    # bogus 0x7FBE0000 free region that swallowed the whole map).
    _fields_ = [("BaseAddress", ctypes.c_void_p),
                ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wt.DWORD),
                ("_pad0", wt.DWORD),
                ("RegionSize", ctypes.c_size_t),
                ("State", wt.DWORD),
                ("Protect", wt.DWORD),
                ("Type", wt.DWORD),
                ("_pad1", wt.DWORD)]


k32.GetCurrentProcess.restype = wt.HANDLE
advapi32.OpenProcessToken.argtypes = [wt.HANDLE, wt.DWORD, ctypes.POINTER(wt.HANDLE)]
advapi32.OpenProcessToken.restype = wt.BOOL
advapi32.LookupPrivilegeValueW.argtypes = [wt.LPCWSTR, wt.LPCWSTR, ctypes.POINTER(LUID)]
advapi32.LookupPrivilegeValueW.restype = wt.BOOL
advapi32.AdjustTokenPrivileges.argtypes = [
    wt.HANDLE, wt.BOOL, ctypes.POINTER(TOKEN_PRIVILEGES), wt.DWORD,
    ctypes.c_void_p, ctypes.POINTER(wt.DWORD)]
advapi32.AdjustTokenPrivileges.restype = wt.BOOL

k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p,
                               ctypes.POINTER(MBI), ctypes.c_size_t]
psapi.GetModuleFileNameExW.argtypes = [wt.HANDLE, ctypes.c_void_p,
                                       wt.LPWSTR, wt.DWORD]
psapi.GetModuleFileNameExW.restype = wt.DWORD


def enable_debug_privilege():
    token = wt.HANDLE()
    if not advapi32.OpenProcessToken(k32.GetCurrentProcess(),
                                     TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                                     ctypes.byref(token)):
        return False, ctypes.get_last_error()
    luid = LUID()
    if not advapi32.LookupPrivilegeValueW(None, "SeDebugPrivilege", ctypes.byref(luid)):
        err = ctypes.get_last_error()
        k32.CloseHandle(token)
        return False, err
    tp = TOKEN_PRIVILEGES()
    tp.PrivilegeCount = 1
    tp.Privileges[0].Luid = luid
    tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
    ctypes.set_last_error(0)
    ok = advapi32.AdjustTokenPrivileges(token, False, ctypes.byref(tp),
                                        ctypes.sizeof(tp), None, None)
    err = ctypes.get_last_error()
    k32.CloseHandle(token)
    return bool(ok) and err == 0, err


def find_pids(name):
    import subprocess
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq " + name, "/FO", "CSV", "/NH"],
            stderr=subprocess.DEVNULL).decode("latin1")
    except Exception:
        return []
    pids = []
    for line in out.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) >= 2 and parts[0].lower() == name.lower():
            try:
                pids.append(int(parts[1]))
            except ValueError:
                pass
    return pids


def regions(h, lo, hi):
    out, addr = [], lo
    mbi = MBI()
    while addr < hi:
        got = k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                                 ctypes.sizeof(mbi))
        if not got:
            break
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize)
        if size <= 0:
            break
        b0, s0 = base, size
        if b0 < lo:
            s0 -= (lo - b0)
            b0 = lo
        if b0 + s0 > hi:
            s0 = hi - b0
        if s0 > 0:
            out.append({"base": b0, "size": s0, "state": int(mbi.State),
                        "protect": int(mbi.Protect), "type": int(mbi.Type)})
        nxt = base + size
        if nxt <= addr:
            break
        addr = nxt
    return out


def read_span(h, lo, hi, regs):
    buf = bytearray(hi - lo)
    fails = 0
    for r in regs:
        if r["state"] != MEM_COMMIT:
            continue
        if r["protect"] & PAGE_GUARD:
            continue
        if (r["protect"] & 0xFF) == PAGE_NOACCESS:
            continue
        b, s, p = r["base"], r["size"], 0
        while p < s:
            n = min(0x10000, s - p)
            tmp = ctypes.create_string_buffer(n)
            got = ctypes.c_size_t()
            ok = k32.ReadProcessMemory(h, ctypes.c_void_p(b + p), tmp, n,
                                       ctypes.byref(got))
            if ok and got.value == n:
                buf[b - lo + p:b - lo + p + n] = tmp.raw[:n]
                p += n
                continue
            n2 = min(0x1000, s - p)
            tmp2 = ctypes.create_string_buffer(n2)
            got2 = ctypes.c_size_t()
            ok2 = k32.ReadProcessMemory(h, ctypes.c_void_p(b + p), tmp2, n2,
                                        ctypes.byref(got2))
            if ok2 and got2.value == n2:
                buf[b - lo + p:b - lo + p + n2] = tmp2.raw[:n2]
            else:
                fails += 1
            p += n2
    return bytes(buf), fails


def find_all(blob, needle):
    out, s = [], 0
    while True:
        i = blob.find(needle, s)
        if i < 0:
            return out
        out.append(i)
        s = i + 1


def xref_scan(blob, lo):
    res = {}
    for name, va in TARGETS.items():
        pat = struct.pack("<I", va)
        entries = []
        for h in find_all(blob, pat):
            where = lo + h
            kind = "code" if any(a <= where < b for a, b in CODE_RANGES) else "data"
            entries.append({"va": where, "kind": kind})
        res[name] = {"target_va": va, "count": len(entries), "hits": entries[:64]}
    return res


def diff_100(prev, cur, lo, cap=400):
    out = []
    if prev is None:
        return out
    n = min(len(prev), len(cur))
    pat = struct.pack("<I", 100)
    s = 0
    while True:
        i = cur.find(pat, s)
        if i < 0:
            break
        s = i + 1
        if i + 4 <= n and prev[i:i + 4] != pat:
            out.append(lo + i)
        if len(out) >= cap:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--pid", type=int)
    ap.add_argument("--proc", default="codoMP_client_shipRetail.exe")
    ap.add_argument("--seconds", type=float, default=45.0)
    ap.add_argument("--step", type=float, default=2.0)
    ap.add_argument("--lo", type=lambda s: int(s, 0), default=LO)
    ap.add_argument("--hi", type=lambda s: int(s, 0), default=HI)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    lo, hi = args.lo, args.hi
    dbg_ok, dbg_err = enable_debug_privilege()
    print("elevated_dbg_privilege=%s err=%d" % (dbg_ok, dbg_err), flush=True)

    pid = args.pid
    if not pid:
        print("waiting for process %s ..." % args.proc, flush=True)
        t_wait = time.time()
        while not find_pids(args.proc):
            if time.time() - t_wait > 90:
                raise SystemExit("process never appeared")
            time.sleep(0.2)
        pid = find_pids(args.proc)[-1]
    print("pid=%d  window 0x%08X..0x%08X" % (pid, lo, hi), flush=True)

    t_open = time.time()
    while True:
        h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
        if h:
            break
        if time.time() - t_open > 30:
            raise SystemExit("cannot open pid %d (err=%d)"
                             % (pid, ctypes.get_last_error()))
        time.sleep(0.25)
    print("OpenProcess ok", flush=True)

    buf = ctypes.create_unicode_buffer(1024)
    n = psapi.GetModuleFileNameExW(h, None, buf, 1024)
    print("main_module=%r" % (buf.value if n else "?"), flush=True)

    regs = regions(h, lo, hi)
    with open(os.path.join(args.out, "regions.json"), "w", encoding="utf-8") as fh:
        json.dump({"pid": pid, "module": buf.value if n else None,
                   "lo": lo, "hi": hi, "regions": regs}, fh, indent=2)
    for r in regs:
        print("  region 0x%08X size 0x%-8X state=0x%X protect=0x%02X type=0x%X"
              % (r["base"], r["size"], r["state"], r["protect"], r["type"]),
              flush=True)

    jsonl = open(os.path.join(args.out, "live.jsonl"), "w", encoding="utf-8")
    t0 = time.time()
    prev, best, best_nz, saved_100 = None, None, -1, False
    first_100_t = None
    empty_streak = 0
    while time.time() - t0 < args.seconds:
        el = time.time() - t0
        blob, fails = read_span(h, lo, hi, regs)
        nz = sum(1 for b in blob if b)
        rec = {"t": round(el, 3), "pid": pid, "nonzero": nz,
               "size": len(blob), "read_fail_pages": fails}

        # re-resolve the map if ACE swapped it mid-run
        if nz == 0:
            empty_streak += 1
            if empty_streak == 3:
                regs = regions(h, lo, hi)
                rec["regions_reloaded"] = len(regs)
                print("  reloaded region map (%d regions)" % len(regs), flush=True)
        else:
            empty_streak = 0

        if nz > 0 and not os.path.exists(os.path.join(args.out, "xrefs.json")):
            xr = xref_scan(blob, lo)
            with open(os.path.join(args.out, "xrefs.json"), "w", encoding="utf-8") as fh:
                json.dump(xr, fh, indent=2)
            rec["xrefs"] = {k: v["count"] for k, v in xr.items()}
            rec["xrefs_code"] = {k: sum(1 for e in v["hits"] if e["kind"] == "code")
                                 for k, v in xr.items()}
            for k, v in xr.items():
                if v["count"]:
                    print("  XREF %-32s VA 0x%08X count=%d code=%d"
                          % (k, v["target_va"], v["count"],
                             sum(1 for e in v["hits"] if e["kind"] == "code")),
                          flush=True)

        hits100 = diff_100(prev, blob, lo)
        if hits100:
            rec["new_100_slots"] = hits100[:80]
            if first_100_t is None:
                first_100_t = el
            print("  t=%6.2fs NEW 100-dwords=%d first=%s"
                  % (el, len(hits100),
                     " ".join("0x%08X" % v for v in hits100[:10])), flush=True)

        jsonl.write(json.dumps(rec) + "\n")
        jsonl.flush()
        print("  t=%6.2fs nonzero=%9d fails=%d" % (el, nz, fails), flush=True)

        if nz > best_nz:
            best, best_nz = blob, nz
        if hits100 and not saved_100:
            saved_100 = True
            with open(os.path.join(args.out, "image_t%06.2fs_100.bin" % el), "wb") as fh:
                fh.write(blob)
        prev = blob
        time.sleep(args.step)

    jsonl.close()
    if best is not None:
        with open(os.path.join(args.out, "image_best.bin"), "wb") as fh:
            fh.write(best)
        print("BEST nonzero=%d -> image_best.bin" % best_nz, flush=True)
    print("first_100_t=%s" % first_100_t, flush=True)
    k32.CloseHandle(h)
    return 0


if __name__ == "__main__":
    sys.exit(main())
