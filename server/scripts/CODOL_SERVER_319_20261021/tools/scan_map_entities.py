# -*- coding: utf-8 -*-
"""Scan a running CODOL client for the map entity string (cm.mapEnts->entityString).

The CLIENT already has the loaded map in memory, as contiguous printable ASCII
    { "classname" "info_player_start" "origin" "x y z" } { ... }
It carries the real spawn points (info_player_start / mp_*_spawn) and the minimap
corners, so reading it avoids decompressing the .ifs fastfile.

Run under the elevated agent (needs PROCESS_VM_READ):
    python -X utf8 scan_map_entities.py <pid> <outfile>
"""
import ctypes, ctypes.wintypes as w, sys, re, json, os

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
READABLE = (0x02, 0x04, 0x20, 0x40)

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", w.DWORD), ("RegionSize", ctypes.c_size_t),
                ("State", w.DWORD), ("Protect", w.DWORD), ("Type", w.DWORD)]

def read(h, addr, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, ctypes.byref(got)):
        return None
    return buf.raw[:got.value]

PRINTABLE = set(range(0x20, 0x7F)) | {0x09, 0x0A, 0x0D}

def expand(blob, pos, maxlen=4 * 1024 * 1024):
    """maximal printable-ASCII run containing pos"""
    a = pos
    while a > 0 and blob[a-1] in PRINTABLE and (pos - a) < maxlen: a -= 1
    b = pos
    n = len(blob)
    while b < n and blob[b] in PRINTABLE and (b - pos) < maxlen: b += 1
    return blob[a:b]

def main():
    if len(sys.argv) < 3:
        print(__doc__); return 2
    pid = int(sys.argv[1]); out = sys.argv[2]
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        print("OpenProcess failed err=%d" % ctypes.get_last_error()); return 1

    mbi = MEMORY_BASIC_INFORMATION()
    addr = 0; needle = b'"classname"'
    found = {}; regions = 0; scanned = 0
    while k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize or 0
        if size == 0: break
        if (mbi.State == MEM_COMMIT and mbi.Protect in READABLE
                and not (mbi.Protect & PAGE_GUARD) and size <= 128 * 1024 * 1024):
            data = read(h, base, size)
            if data:
                regions += 1; scanned += len(data)
                i = 0
                while True:
                    j = data.find(needle, i)
                    if j < 0: break
                    run = expand(data, j)
                    if b'"origin"' in run or b'info_player' in run or b'spawn' in run:
                        key = len(run)
                        found[(base, key, run[:64])] = (base, run)
                    i = j + 1
        addr = base + size
        if addr > 0x7FFFFFFF: break

    print("regions=%d scanned=%.1fMB candidate_blobs=%d" % (regions, scanned/1048576.0, len(found)))
    blobs = list(found.values())
    blobs.sort(key=lambda t: -len(t[1]))
    with open(out, "w", encoding="utf-8") as f:
        for (va, run) in blobs[:8]:
            f.write("# VA=0x%08X len=%d\n" % (va, len(run)))
            f.write(run.decode("latin-1") + "\n")
    print("wrote %s (%d blobs)" % (out, min(8, len(blobs))))
    if blobs:
        txt = blobs[0][1].decode("latin-1")
        names = re.findall(r'"classname"\s+"([^"]+)"', txt)
        from collections import Counter
        print("classname census (top):", Counter(names).most_common(15))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
