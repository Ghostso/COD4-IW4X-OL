# -*- coding: utf-8 -*-
"""
_dyn100_mem.py -- read-only pre-arm memory evidence for the in-game
"[100] failed to connect to lobby service" panel.

DYNAMIC task.  Read-only observation only:
  * CreateProcess(CREATE_SUSPENDED) so the game handle is taken BEFORE ACE
    arms (the ordinary attach path is denied with err=5 by ACE),
  * OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ) on that handle
    -- explicitly READ-ONLY, no write, no inject, no patch,
  * ResumeThread, then poll the main module image over time with
    ReadProcessMemory and record:
      - every 4-byte LE reference to the lobby strings (code vs data)
      - the first moment a dword 100 appears in a previously-empty slot
      - a memory snapshot at that moment

Nothing is written to the target.  No network is touched.  No ACE driver is
touched.

Usage:
    python -X utf8 _dyn100_mem.py --exe <game.exe> --cwd <sandbox> \
        --out <dir> --seconds 90 --step 2
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import sys
import time

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)

CREATE_SUSPENDED = 0x00000004
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01

TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002
SE_DEBUG_NAME = 'SeDebugPrivilege'

# Main module window.  Preferred base 0x00400000, image spans to ~0x00E65000.
# Full module window: SizeOfImage = 0x0E659000, so the image ends at
# 0x00400000 + 0x0E659000 = 0x0EA59000.  The old HI=0x00E65000 covered only
# the first 10.4 MB (4.5%) and completely missed the 219.7 MB third .tp3
# section that starts at RVA 0x00A16000.
LO = 0x00400000
HI = 0x0EA59000

# The packed-code region is RVA < 0x594000; the VM-decrypted gap is
# 0x00994000..0x00CA8000.  Both are "code" for the purpose of classifying
# xref hits.
CODE_RANGES = [(0x00401000, 0x00994000), (0x00994000, 0x00CA8000)]

TARGETS = {
    "SF_UI_DW_LIVE_CONNECTING_FAILED": 0x00DE0640,
    "SF_UI_DW_LIVE_DISCONNECTED": 0x00DBD888,
    "SF_UI_DW_LIVE_CERT_FAILED": 0x00DE09F0,
    "DW_LOBBY_ERROR": 0x00DE0990,
    "DW_LOBBY_CONNECTED": 0x00DE0938,
    "DW_DNS_ERROR": 0x00DE08D8,
    "DW_ACCOUNT_ERROR": 0x00DE08F8,
    "dwLogonStart": 0x00DE08C8,
    "cppOnDWConnected": 0x00DE05FC,
    "cppOnDWDisconnected": 0x00DE05E8,
    "bdLobbyErrorCode": 0x00AD27F0,
    "BD_MAX_ERROR_CODE": 0x00AD27D4,
    "Unknown_bdLobbyErrorCode": 0x00AD27E8,
    "WIN_IIPS_INIT_ERROR": 0x00DC93A8,
    "TQOS_HOST_ied_tqos": 0x00DD98A0,
}


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [('cb', wt.DWORD), ('lpReserved', wt.LPWSTR), ('lpDesktop', wt.LPWSTR),
                ('lpTitle', wt.LPWSTR), ('dwX', wt.DWORD), ('dwY', wt.DWORD),
                ('dwXSize', wt.DWORD), ('dwYSize', wt.DWORD),
                ('dwXCountChars', wt.DWORD), ('dwYCountChars', wt.DWORD),
                ('dwFillAttribute', wt.DWORD), ('dwFlags', wt.DWORD),
                ('wShowWindow', wt.WORD), ('cbReserved2', wt.WORD),
                ('lpReserved2', ctypes.c_void_p), ('hStdInput', wt.HANDLE),
                ('hStdOutput', wt.HANDLE), ('hStdError', wt.HANDLE)]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [('hProcess', wt.HANDLE), ('hThread', wt.HANDLE),
                ('dwProcessId', wt.DWORD), ('dwThreadId', wt.DWORD)]


class MBI(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_void_p), ('AllocationBase', ctypes.c_void_p),
                ('AllocationProtect', wt.DWORD), ('_pad0', wt.DWORD),
                ('RegionSize', ctypes.c_size_t), ('State', wt.DWORD),
                ('Protect', wt.DWORD), ('Type', wt.DWORD), ('_pad1', wt.DWORD)]


class LUID(ctypes.Structure):
    _fields_ = [('LowPart', wt.DWORD), ('HighPart', wt.LONG)]


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [('Luid', LUID), ('Attributes', wt.DWORD)]


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [('PrivilegeCount', wt.DWORD),
                ('Privileges', LUID_AND_ATTRIBUTES * 1)]


k32.GetCurrentProcess.restype = wt.HANDLE
advapi32.OpenProcessToken.argtypes = [wt.HANDLE, wt.DWORD, ctypes.POINTER(wt.HANDLE)]
advapi32.OpenProcessToken.restype = wt.BOOL
advapi32.LookupPrivilegeValueW.argtypes = [wt.LPCWSTR, wt.LPCWSTR, ctypes.POINTER(LUID)]
advapi32.LookupPrivilegeValueW.restype = wt.BOOL
advapi32.AdjustTokenPrivileges.argtypes = [
    wt.HANDLE, wt.BOOL, ctypes.POINTER(TOKEN_PRIVILEGES), wt.DWORD,
    ctypes.c_void_p, ctypes.POINTER(wt.DWORD)]
advapi32.AdjustTokenPrivileges.restype = wt.BOOL
k32.CreateProcessW.restype = wt.BOOL
k32.CreateProcessW.argtypes = [wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p,
                               ctypes.c_void_p, wt.BOOL, wt.DWORD, ctypes.c_void_p,
                               wt.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p]
k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p,
                               ctypes.POINTER(MBI), ctypes.c_size_t]
k32.ResumeThread.argtypes = [wt.HANDLE]


def enable_debug():
    token = wt.HANDLE()
    if not advapi32.OpenProcessToken(k32.GetCurrentProcess(),
                                     TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                                     ctypes.byref(token)):
        return False, ctypes.get_last_error()
    luid = LUID()
    if not advapi32.LookupPrivilegeValueW(None, SE_DEBUG_NAME, ctypes.byref(luid)):
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
            n = min(0x40000, s - p)
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
        res[name] = {"target_va": va, "count": len(entries), "hits": entries[:128]}
    return res


def diff_100(prev, cur, lo, cap=800):
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
    ap.add_argument("--exe", required=True)
    ap.add_argument("--cwd", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float, default=90.0)
    ap.add_argument("--step", type=float, default=2.0)
    ap.add_argument("--args", default="-q --disable-gpu --disable-gpu-compositing")
    ap.add_argument("--resume", type=int, default=1,
                    help="1 = resume the suspended process (default)")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    ok, err = enable_debug()
    print("SeDebugPrivilege=%s err=%d" % (ok, err), flush=True)

    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    cmd = '"%s" %s' % (args.exe, args.args)
    buf = ctypes.create_unicode_buffer(cmd)
    if not k32.CreateProcessW(args.exe, buf, None, None, True,
                              CREATE_SUSPENDED, None, args.cwd,
                              ctypes.byref(si), ctypes.byref(pi)):
        raise SystemExit('CreateProcess failed err=%d' % ctypes.get_last_error())
    pid = pi.dwProcessId
    print("created suspended pid=%d" % pid, flush=True)

    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    print("pre-arm OpenProcess(READ|QUERY) -> %s err=%d"
          % (h, ctypes.get_last_error()), flush=True)
    if not h:
        k32.TerminateProcess(pi.hProcess, 1)
        raise SystemExit("read handle unavailable")

    if args.resume:
        k32.ResumeThread(pi.hThread)
        print("resumed", flush=True)

    jsonl = open(os.path.join(args.out, "live.jsonl"), "w", encoding="utf-8")
    t0 = time.time()
    prev, best, best_nz = None, None, -1
    regs = regions(h, LO, HI)
    with open(os.path.join(args.out, "regions.json"), "w", encoding="utf-8") as fh:
        json.dump({"pid": pid, "lo": LO, "hi": HI, "regions": regs}, fh, indent=2)
    for r in regs:
        print("  region 0x%08X size 0x%-8X state=0x%X protect=0x%02X type=0x%X"
              % (r["base"], r["size"], r["state"], r["protect"], r["type"]),
              flush=True)

    first_100_t = None
    saved_100 = False
    empty_streak = 0
    while time.time() - t0 < args.seconds:
        el = time.time() - t0
        blob, fails = read_span(h, LO, HI, regs)
        nz = sum(1 for b in blob if b)
        rec = {"t": round(el, 3), "pid": pid, "nonzero": nz,
               "size": len(blob), "read_fail_pages": fails}
        if nz == 0:
            empty_streak += 1
            if empty_streak == 3:
                regs = regions(h, LO, HI)
                rec["regions_reloaded"] = len(regs)
                print("  reloaded region map (%d regions)" % len(regs), flush=True)
        else:
            empty_streak = 0

        if nz > 0 and not os.path.exists(os.path.join(args.out, "xrefs.json")):
            xr = xref_scan(blob, LO)
            with open(os.path.join(args.out, "xrefs.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(xr, fh, indent=2)
            for k, v in xr.items():
                if v["count"]:
                    code = sum(1 for e in v["hits"] if e["kind"] == "code")
                    print("  XREF %-34s VA 0x%08X count=%d code=%d"
                          % (k, v["target_va"], v["count"], code), flush=True)

        hits100 = diff_100(prev, blob, LO)
        if hits100:
            rec["new_100_slots"] = hits100[:120]
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
            with open(os.path.join(args.out, "image_t%06.2fs_100.bin" % el),
                      "wb") as fh:
                fh.write(blob)
        prev = blob
        time.sleep(args.step)

    jsonl.close()
    if best is not None:
        with open(os.path.join(args.out, "image_best.bin"), "wb") as fh:
            fh.write(best)
        print("BEST nonzero=%d -> image_best.bin" % best_nz, flush=True)
    print("first_100_t=%s" % first_100_t, flush=True)
    print("pid=%d left running; orchestrator kills it" % pid, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
