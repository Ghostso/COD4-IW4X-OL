# -*- coding: utf-8 -*-
"""full_image_dump.py -- full module image dump for static analysis.

Reads the entire client module image [ImageBase, ImageBase+SizeOfImage) and
writes a sparse map in the same 'RG' container used by the existing dumps:
    repeat { b'RG'; u32 va; u32 size; bytes[size] }

Only committed/readable regions are emitted; gaps are recorded in the index
JSON so the reconstruction is verifiable.

Usage:  python -X utf8 full_image_dump.py <pid> <out_prefix>
"""
import ctypes, ctypes.wintypes as wt, json, os, struct, sys

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01
READABLE = (0x02, 0x04, 0x20, 0x40, 0x80)

class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p),
                ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wt.DWORD),
                ("RegionSize", ctypes.c_size_t),
                ("State", wt.DWORD),
                ("Protect", wt.DWORD),
                ("Type", wt.DWORD)]

def main():
    if len(sys.argv) < 3:
        print(__doc__); return 2
    pid = int(sys.argv[1]); prefix = sys.argv[2]

    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        print("OpenProcess failed err=%d" % ctypes.get_last_error()); return 1

    # resolve module range by reading the PE header at the image base.
    # Toolhelp snapshot is unreliable under this protection, so parse the
    # in-memory DOS/NT headers instead.
    base = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x400000
    hdr = ctypes.create_string_buffer(0x1000)
    got = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(base), hdr, 0x1000, ctypes.byref(got)) or got.value < 0x200:
        print("cannot read PE header err=%d" % ctypes.get_last_error()); return 1
    hb = hdr.raw
    if hb[:2] != b"MZ":
        print("no MZ at 0x%X" % base); return 1
    e_lfanew = struct.unpack_from("<I", hb, 0x3C)[0]
    if hb[e_lfanew:e_lfanew+4] != b"PE\0\0":
        print("no PE sig"); return 1
    opt = e_lfanew + 4 + 20
    size = struct.unpack_from("<I", hb, opt + 56)[0]

    print("module base=0x%X size=0x%X" % (base or 0, size or 0))
    if not base or not size:
        print("cannot resolve module range"); return 1

    outpath = prefix + ".bin"
    idx = {"pid": pid, "base": base, "size": size, "regions": [], "gaps": []}
    with open(outpath, "wb") as f:
        addr = base; end = base + size
        mbi = MBI()
        while addr < end:
            if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
                break
            rbase = mbi.BaseAddress or 0
            rsize = mbi.RegionSize or 0
            if rsize == 0: break
            readable = (mbi.State == MEM_COMMIT and
                        (mbi.Protect & 0xFF) in READABLE and
                        not (mbi.Protect & PAGE_GUARD))
            if readable:
                buf = ctypes.create_string_buffer(rsize)
                got = ctypes.c_size_t(0)
                ok = k32.ReadProcessMemory(h, ctypes.c_void_p(rbase), buf, rsize, ctypes.byref(got))
                if ok and got.value:
                    data = buf.raw[:got.value]
                    f.write(b"RG" + struct.pack("<II", rbase, len(data)) + data)
                    idx["regions"].append({"va": rbase, "size": len(data)})
                else:
                    idx["gaps"].append({"va": rbase, "size": rsize,
                                        "err": ctypes.get_last_error()})
            else:
                idx["gaps"].append({"va": rbase, "size": rsize,
                                    "protect": mbi.Protect, "state": mbi.State})
            addr = rbase + rsize
    k32.CloseHandle(h)

    with open(prefix + ".json", "w", encoding="utf-8") as f:
        json.dump(idx, f, indent=1)
    total = sum(r["size"] for r in idx["regions"])
    print("wrote %s : %d regions, %.1f MB, %d gaps" %
          (outpath, len(idx["regions"]), total/1048576.0, len(idx["gaps"])))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
