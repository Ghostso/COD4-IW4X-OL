"""Derive file-offset -> VA mapping from the real section table.

Reads only. Writes nothing except stdout. ASCII only.
"""
import struct
import os
import json


EXE = os.path.join(
    r"D:\BaiduNetdiskDownload\使命召唤OL",
    "run_codol_001", "sandbox_ifs1_20260923",
    "codoMP_client_shipRetail.exe")


def sections(path):
    d = open(path, "rb").read()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    optsz = struct.unpack_from("<H", d, pe + 20)[0]
    base = struct.unpack_from("<I", d, pe + 24 + 28)[0]
    off = pe + 24 + optsz
    out = []
    for i in range(nsec):
        s = d[off + i * 40: off + (i + 1) * 40]
        name = s[:8].rstrip(b"\x00").decode("latin1")
        vsize, vaddr, rsize, raddr = struct.unpack_from("<IIII", s, 8)
        out.append({
            "name": name,
            "va": vaddr,
            "vsize": vsize,
            "raw": raddr,
            "rsize": rsize,
        })
    return base, out


def off_to_va(secs, foff):
    for s in secs:
        if s["raw"] <= foff < s["raw"] + s["rsize"]:
            return s["va"] + (foff - s["raw"])
    return None


def va_to_off(secs, va):
    for s in secs:
        if s["va"] <= va < s["va"] + max(s["vsize"], s["rsize"]):
            return s["raw"] + (va - s["va"])
    return None


def main():
    base, secs = sections(EXE)
    print("ImageBase = 0x%X" % base)
    print()
    for s in secs:
        print("%-6s VA=0x%08X raw=0x%08X vsize=0x%08X rsize=0x%08X"
              % (s["name"], s["va"], s["raw"], s["vsize"], s["rsize"]))
    print()
    # Known string/anchor offsets from earlier work, checked mechanically.
    probes = [
        ("dwLobby string pool base raw", 0x702000),
        ("dl-tqos string raw", 0x6C58A0),
        ("tvm0 raw", 0x76F000),
    ]
    for label, foff in probes:
        va = off_to_va(secs, foff)
        print("%-30s raw=0x%08X -> VA=%s"
              % (label, foff, ("0x%08X" % (base + va)) if va else "UNMAPPED"))
    print()
    va_list = [
        0x00DD98A0,   # ied-tqos.qq.com string (claimed)
        0x00DE0640,   # UI key string (claimed)
        0x00D5A2CC,   # https://%s:%d/auth/ (claimed)
        0x008037D9,   # earlier claimed patch site
        0x008037C4,   # earlier claimed func start
    ]
    for va in va_list:
        off = va_to_off(secs, va - base)
        print("VA=0x%08X -> raw=%s"
              % (va, ("0x%X" % off) if off else "UNMAPPED"))
    print()
    print(json.dumps({"imagebase": hex(base)}, indent=2))


if __name__ == "__main__":
    main()
