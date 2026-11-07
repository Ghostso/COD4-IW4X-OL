# -*- coding: utf-8 -*-
"""
_m4_full_image.py - mainline: full-image runtime dump of the CODOL engine.

WHY: the existing dumps (engine_dump.py) start at VA 0x00994000 and therefore
cover only RVA >= 0x594000. Every direct xref to
@SF_UI_DW_LIVE_CONNECTING_FAILED (RVA 0x9E0640) was absent from those dumps,
which means the code that raises the [100] panel lives BELOW RVA 0x594000.
This tool dumps the whole module window from the preferred base instead.

Read-only: OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ) + ReadProcessMemory.
It does NOT inject, does NOT patch, does NOT change the network.

Usage:
    python _m4_full_image.py <pid> --out <dir> [--seconds 30] [--step 3]
    python _m4_full_image.py --list

Outputs (in <dir>):
    image_<t>s.bin        raw bytes of the whole window at that sample
    image_diff.jsonl      per-sample per-64KB nonzero/change statistics
    image_best.bin        the densest sample
    image_map.txt         VA map of every committed region and its protect
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import sys
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
PAGE = 0x1000

MEM_COMMIT = 0x1000
MEM_FREE = 0x10000
MEM_RESERVE = 0x2000

PROT = {
    0x01: "NOACCESS", 0x02: "R", 0x04: "RW", 0x08: "WC",
    0x10: "X", 0x20: "RX", 0x40: "RWX", 0x80: "WCX",
}


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wt.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wt.DWORD),
        ("Protect", wt.DWORD),
        ("Type", wt.DWORD),
    ]


k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p,
                               ctypes.POINTER(MEMORY_BASIC_INFORMATION),
                               ctypes.c_size_t]


def open_pid(pid):
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        raise SystemExit("OpenProcess(%d) failed err=%d (need admin / ACE)"
                         % (pid, ctypes.get_last_error()))
    return h


def enum_regions(h, lo, hi):
    out = []
    addr = lo
    mbi = MEMORY_BASIC_INFORMATION()
    while addr < hi:
        got = k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                                 ctypes.sizeof(mbi))
        if not got:
            break
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize)
        if base < lo:
            size -= (lo - base)
            base = lo
        if base + size > hi:
            size = hi - base
        out.append({
            "base": base, "size": size, "state": int(mbi.State),
            "protect": int(mbi.Protect), "type": int(mbi.Type),
        })
        nxt = int(mbi.BaseAddress or 0) + int(mbi.RegionSize)
        if nxt <= addr:
            break
        addr = nxt
    return out


def read_block(h, base, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t()
    ok = k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, size,
                               ctypes.byref(got))
    if ok and got.value == size:
        return buf.raw[:size]
    return None


def read_span(h, lo, hi):
    """Read [lo,hi) honoring each committed region; unreadable -> zeros."""
    out = bytearray(hi - lo)
    for r in enum_regions(h, lo, hi):
        if r["state"] != MEM_COMMIT:
            continue
        if r["protect"] & 0x100:      # PAGE_GUARD
            continue
        b, s = r["base"], r["size"]
        p = 0
        while p < s:
            n = min(0x10000, s - p)
            chunk = read_block(h, b + p, n)
            if chunk is None:
                # fall back to page granularity
                n2 = min(PAGE, s - p)
                chunk = read_block(h, b + p, n2)
                if chunk is not None:
                    out[b - lo + p: b - lo + p + n2] = chunk
                p += n2
                continue
            out[b - lo + p: b - lo + p + n] = chunk
            p += n
    return bytes(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pid", nargs="?", type=int)
    ap.add_argument("--out", default=os.path.join(
        r"D:\BaiduNetdiskDownload\使命召唤OL", "CODOLServer", "_fullimage"))
    ap.add_argument("--seconds", type=int, default=30)
    ap.add_argument("--step", type=float, default=3.0)
    ap.add_argument("--lo", type=lambda s: int(s, 0), default=0x00400000)
    ap.add_argument("--hi", type=lambda s: int(s, 0), default=0x00E65000)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if not args.pid:
        raise SystemExit("need <pid>")

    os.makedirs(args.out, exist_ok=True)
    h = open_pid(args.pid)
    lo, hi = args.lo, args.hi
    print("pid=%d  window 0x%08X..0x%08X  (%d bytes)" % (args.pid, lo, hi, hi - lo))

    regions = enum_regions(h, lo, hi)
    with open(os.path.join(args.out, "image_map.txt"), "w", encoding="utf-8") as fh:
        for r in regions:
            line = ("0x%08X  0x%08X  state=0x%04X protect=0x%02X(%s) type=0x%X"
                    % (r["base"], r["size"], r["state"], r["protect"],
                       PROT.get(r["protect"] & 0xFF, "?"), r["type"]))
            print("  " + line)
            fh.write(line + "\n")

    jsonl = open(os.path.join(args.out, "image_diff.jsonl"), "w", encoding="utf-8")
    best, best_nz, best_t, prev = None, -1, 0.0, None
    t0 = time.time()
    i = 0
    while time.time() - t0 < args.seconds:
        el = time.time() - t0
        blob = read_span(h, lo, hi)
        nz = sum(1 for b in blob if b)
        changed = 0
        if prev is not None:
            changed = sum(1 for a, b in zip(blob, prev) if a != b)
        rec = {"t": round(el, 3), "nonzero": nz, "changed_vs_prev": changed,
               "size": len(blob)}
        jsonl.write(json.dumps(rec) + "\n")
        jsonl.flush()
        print("  t=%6.2fs nonzero=%9d changed=%9d" % (el, nz, changed))
        if i in (0, 1) or changed < 40000:
            path = os.path.join(args.out, "image_%06.2fs.bin" % el)
            with open(path, "wb") as bf:
                bf.write(blob)
        if nz > best_nz:
            best, best_nz, best_t = blob, nz, el
        prev = blob
        i += 1
        time.sleep(args.step)
    jsonl.close()

    if best is not None:
        with open(os.path.join(args.out, "image_best.bin"), "wb") as bf:
            bf.write(best)
        print("BEST t=%.2fs nonzero=%d -> image_best.bin" % (best_t, best_nz))
    return 0


if __name__ == "__main__":
    sys.exit(main())
