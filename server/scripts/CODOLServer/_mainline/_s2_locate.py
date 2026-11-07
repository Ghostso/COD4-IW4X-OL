# -*- coding: utf-8 -*-
"""S2-A: locate enable_iips / iips_url readers and IIPS init call sites.

Pure static: file reads only. No game launch, no injection, no net changes.
"""
import sys, re, struct, json, os

try:
    import pefile
    import capstone
except Exception as e:
    print("missing lib", e)
    sys.exit(2)


def find_all(buf, needle):
    out = []
    start = 0
    while True:
        i = buf.find(needle, start)
        if i < 0:
            return out
        out.append(i)
        start = i + 1


def ascii16(s):
    return s.encode("utf-16-le") + b"\x00\x00"


def rva_of_offset(pe, off):
    for s in pe.sections:
        raw = s.PointerToRawData
        if raw <= off < raw + s.SizeOfRawData:
            return off - raw + s.VirtualAddress, s.Name.rstrip(b"\x00").decode("latin1")
    return None, None


def va_of_offset(pe, off):
    rva, name = rva_of_offset(pe, off)
    if rva is None:
        return None, None
    return pe.OPTIONAL_HEADER.ImageBase + rva, name


def refs_to_va(pe, img, va):
    """Find absolute dword refs equal to va and rel-induced refs."""
    pat = struct.pack("<I", va & 0xFFFFFFFF)
    hits = find_all(img, pat)
    return hits


def main():
    path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories()
    img = open(path, "rb").read()
    base = pe.OPTIONAL_HEADER.ImageBase

    rep = {"file": os.path.basename(path), "size": len(img), "imagebase": hex(base), "hits": {}}

    # 1. literal ASCII strings of interest
    targets = [
        b"iips.ini", b"enable_iips", b"iips_url", b"iips_debug",
        b"IIPSHostApp.exe", b"iips.dll", b"IFS2.dll", b"ifs2.dll",
        b"create_iips", b"IIPS", b"This is a share state",
        b"iips_policymsg", b"ResourceManagerII", b"InitInGameApp",
        b"iips_enableOptionalDownloads", b"HostPid", b"IIPSHost",
    ]
    for t in targets:
        occ = []
        for off in find_all(img, t):
            va, sec = va_of_offset(pe, off)
            occ.append({"off": hex(off), "va": hex(va) if va else None, "sec": sec})
        if occ:
            rep["hits"].setdefault("ascii", {})[t.decode("latin1")] = occ

    # wide strings too
    for t in [b"iips.ini", b"enable_iips", b"IIPSHostApp.exe", b"iips.dll", b"IIPS"]:
        w = ascii16(t.decode("latin1"))
        occ = []
        for off in find_all(img, w):
            va, sec = va_of_offset(pe, off)
            occ.append({"off": hex(off), "va": hex(va) if va else None, "sec": sec})
        if occ:
            rep["hits"].setdefault("wide", {})[t.decode("latin1")] = occ

    # 2. absolute dword references to those VAs
    rep["abs_refs"] = {}
    for kind, table in rep["hits"].items():
        for name, occ in table.items():
            for e in occ:
                if not e["va"]:
                    continue
                va = int(e["va"], 16)
                refs = refs_to_va(pe, img, va)
                if refs:
                    key = "%s@%s" % (name, e["va"])
                    rep["abs_refs"][key] = [
                        {"off": hex(o), "va": hex(va_of_offset(pe, o)[0]) if va_of_offset(pe, o)[0] else None}
                        for o in refs
                    ]

    txt = json.dumps(rep, indent=1, ensure_ascii=False)
    if out:
        open(out, "w", encoding="utf-8").write(txt)
    print(txt)


if __name__ == "__main__":
    main()
