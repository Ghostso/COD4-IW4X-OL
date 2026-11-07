"""Agent 01/02: full PE structure dump + diff between original iips.dll and LocalRM.dll.

Read-only. Never writes to the templates.
"""
import hashlib
import os
import struct
import sys

import pefile

ORIG = r"COD OL\IIPS\iips.dll"
GEN = "LocalRM.dll"

DIRNAMES = [
    "EXPORT", "IMPORT", "RESOURCE", "EXCEPTION", "SECURITY", "BASERELOC",
    "DEBUG", "ARCHITECTURE", "GLOBALPTR", "TLS", "LOAD_CONFIG", "BOUND_IMPORT",
    "IAT", "DELAY_IMPORT", "COM_DESCRIPTOR", "RESERVED",
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sect_name(s):
    return s.Name.rstrip(b"\x00").decode("latin-1")


def dump(path):
    pe = pefile.PE(path, fast_load=True)
    out = {}
    out["path"] = path
    out["size"] = os.path.getsize(path)
    out["sha256"] = sha256(path)
    fh = pe.FILE_HEADER
    oh = pe.OPTIONAL_HEADER
    out["dos"] = {"e_magic": pe.DOS_HEADER.e_magic, "e_lfanew": pe.DOS_HEADER.e_lfanew}
    out["coff"] = {
        "Machine": fh.Machine,
        "NumberOfSections": fh.NumberOfSections,
        "TimeDateStamp": fh.TimeDateStamp,
        "PointerToSymbolTable": fh.PointerToSymbolTable,
        "NumberOfSymbols": fh.NumberOfSymbols,
        "SizeOfOptionalHeader": fh.SizeOfOptionalHeader,
        "Characteristics": fh.Characteristics,
    }
    out["opthdr"] = {
        "Magic": oh.Magic,
        "AddressOfEntryPoint": oh.AddressOfEntryPoint,
        "ImageBase": oh.ImageBase,
        "SectionAlignment": oh.SectionAlignment,
        "FileAlignment": oh.FileAlignment,
        "SizeOfCode": oh.SizeOfCode,
        "SizeOfInitializedData": oh.SizeOfInitializedData,
        "SizeOfUninitializedData": oh.SizeOfUninitializedData,
        "SizeOfImage": oh.SizeOfImage,
        "SizeOfHeaders": oh.SizeOfHeaders,
        "Subsystem": oh.Subsystem,
        "DllCharacteristics": oh.DllCharacteristics,
        "SizeOfStackReserve": oh.SizeOfStackReserve,
        "SizeOfStackCommit": oh.SizeOfStackCommit,
        "SizeOfHeapReserve": oh.SizeOfHeapReserve,
        "SizeOfHeapCommit": oh.SizeOfHeapCommit,
        "NumberOfRvaAndSizes": oh.NumberOfRvaAndSizes,
        "BaseOfCode": oh.BaseOfCode,
        "BaseOfData": oh.BaseOfData,
        "CheckSum": oh.CheckSum,
        "LoaderFlags": oh.LoaderFlags,
    }
    out["sections"] = []
    for s in pe.sections:
        out["sections"].append({
            "Name": sect_name(s),
            "VirtualSize": s.Misc_VirtualSize,
            "VirtualAddress": s.VirtualAddress,
            "SizeOfRawData": s.SizeOfRawData,
            "PointerToRawData": s.PointerToRawData,
            "Characteristics": s.Characteristics,
            "PointerToRelocations": s.PointerToRelocations,
            "NumberOfRelocations": s.NumberOfRelocations,
            "PointerToLinenumbers": s.PointerToLinenumbers,
            "NumberOfLinenumbers": s.NumberOfLinenumbers,
        })
    out["dirs"] = []
    for i in range(min(16, len(oh.DATA_DIRECTORY))):
        d = oh.DATA_DIRECTORY[i]
        out["dirs"].append({"idx": i, "name": DIRNAMES[i], "VA": d.VirtualAddress, "Size": d.Size})
    pe.close()
    return out


def fmt(v, w=10):
    if isinstance(v, int):
        return ("0x%X" % v).rjust(w)
    return str(v).rjust(w)


def report(a, b):
    lines = []
    p = lines.append
    p("=" * 78)
    p("AGENT 01 — ORIGINAL vs GENERATED PE STRUCTURE DIFF")
    p("=" * 78)
    p("ORIGINAL : %s  (%d bytes)" % (a["path"], a["size"]))
    p("           SHA256 %s" % a["sha256"])
    p("GENERATED: %s  (%d bytes)" % (b["path"], b["size"]))
    p("           SHA256 %s" % b["sha256"])
    p("")

    def cmp_block(title, ka, kb):
        p("--- %s ---" % title)
        p("%-28s %14s %14s   %s" % ("field", "original", "generated", "verdict"))
        for k in ka:
            va, vb = ka[k], kb.get(k)
            same = (va == vb)
            p("%-28s %14s %14s   %s" % (
                k,
                ("0x%X" % va) if isinstance(va, int) else str(va),
                ("0x%X" % vb) if isinstance(vb, int) else str(vb),
                "same" if same else "**CHANGED**",
            ))
        p("")

    cmp_block("DOS HEADER", a["dos"], b["dos"])
    cmp_block("COFF HEADER", a["coff"], b["coff"])
    cmp_block("OPTIONAL HEADER", a["opthdr"], b["opthdr"])

    p("--- DATA DIRECTORIES ---")
    p("%-3s %-16s %12s %10s %12s %10s  %s" % ("#", "name", "orig VA", "orig Sz", "gen VA", "gen Sz", "verdict"))
    for da, db in zip(a["dirs"], b["dirs"]):
        same = (da["VA"] == db["VA"] and da["Size"] == db["Size"])
        p("%-3d %-16s %12s %10s %12s %10s  %s" % (
            da["idx"], da["name"],
            "0x%X" % da["VA"], "0x%X" % da["Size"],
            "0x%X" % db["VA"], "0x%X" % db["Size"],
            "same" if same else "**CHANGED**",
        ))
    p("")

    p("=" * 78)
    p("AGENT 02 — SECTION TABLE DIFF")
    p("=" * 78)
    p("orig sections = %d, gen sections = %d" % (len(a["sections"]), len(b["sections"])))
    p("")
    for i in range(max(len(a["sections"]), len(b["sections"]))):
        sa = a["sections"][i] if i < len(a["sections"]) else None
        sb = b["sections"][i] if i < len(b["sections"]) else None
        p("--- section index %d ---" % i)
        fields = ["Name", "VirtualSize", "VirtualAddress", "SizeOfRawData",
                  "PointerToRawData", "Characteristics", "NumberOfRelocations"]
        p("%-22s %14s %14s   %s" % ("field", "original", "generated", "verdict"))
        for f in fields:
            va = sa[f] if sa else None
            vb = sb[f] if sb else None
            def s(v):
                if v is None:
                    return "N/A"
                if isinstance(v, int):
                    return "0x%X" % v
                return str(v)
            p("%-22s %14s %14s   %s" % (f, s(va), s(vb), "same" if va == vb else "**CHANGED**"))
        p("")
    return "\n".join(lines)


def structural_checks(d):
    """Static anomalies for a single PE."""
    lines = []
    p = lines.append
    oh = d["opthdr"]
    fa = oh["FileAlignment"]
    sa = oh["SectionAlignment"]
    p("--- alignment / overlap checks (%s) ---" % d["path"])
    if fa == 0:
        p("FileAlignment = 0  -> **BAD_ALIGNMENT** (div by zero risk)")
    vspans = []
    rspans = []
    for s in d["sections"]:
        nm = s["Name"]
        if sa and s["VirtualAddress"] % sa:
            p("%s: VirtualAddress 0x%X not %d-aligned **BAD_ALIGNMENT**" % (nm, s["VirtualAddress"], sa))
        if fa and s["PointerToRawData"] % fa:
            p("%s: PointerToRawData 0x%X not %d-aligned **BAD_ALIGNMENT**" % (nm, s["PointerToRawData"], fa))
        if fa and s["SizeOfRawData"] % fa:
            p("%s: SizeOfRawData 0x%X not %d-aligned **BAD_ALIGNMENT**" % (nm, s["SizeOfRawData"], fa))
        if s["SizeOfRawData"] < s["VirtualSize"] and fa:
            # legal only when the tail is all-zero (bss-like); flag for review
            p("%s: SizeOfRawData(0x%X) < VirtualSize(0x%X)  [bss-tail rule, review]"
              % (nm, s["SizeOfRawData"], s["VirtualSize"]))
        vspans.append((s["VirtualAddress"], s["VirtualAddress"] + max(s["VirtualSize"], s["SizeOfRawData"]), nm))
        rspans.append((s["PointerToRawData"], s["PointerToRawData"] + s["SizeOfRawData"], nm))
    def overlaps(spans, label):
        spans = sorted(spans)
        for i in range(len(spans) - 1):
            a0, a1, an = spans[i]
            b0, b1, bn = spans[i + 1]
            if b0 < a1 and a0 and b0:
                p("%s OVERLAP: %s [0x%X-0x%X) vs %s [0x%X-0x%X)  **BAD_ALIGNMENT/OVERLAP**"
                  % (label, an, a0, a1, bn, b0, b1))
    overlaps(rspans, "RAW")
    imgsz = oh["SizeOfImage"]
    if vspans:
        last = max(v[1] for v in vspans)
        if last > imgsz:
            p("SizeOfImage 0x%X < highest section end 0x%X  **BAD_IMAGE_SIZE**" % (imgsz, last))
    p("SizeOfHeaders = 0x%X ; first raw section offset = 0x%X"
      % (oh["SizeOfHeaders"], min([s["PointerToRawData"] for s in d["sections"]] or [0])))
    if d["sections"] and min(s["PointerToRawData"] for s in d["sections"]) < oh["SizeOfHeaders"]:
        p("**BAD_ALIGNMENT**: first section raw data starts inside headers")
    for i, dd in enumerate(d["dirs"]):
        if dd["VA"] and dd["VA"] >= imgsz:
            p("dir %d (%s) VA 0x%X beyond SizeOfImage 0x%X **BAD_IMAGE_SIZE**"
              % (i, dd["name"], dd["VA"], imgsz))
    p("done")
    return "\n".join(lines)


if __name__ == "__main__":
    a = dump(ORIG)
    b = dump(GEN)
    print(report(a, b))
    print()
    print("=" * 78)
    print("STATIC STRUCTURAL CHECKS")
    print("=" * 78)
    print(structural_checks(a))
    print()
    print(structural_checks(b))
