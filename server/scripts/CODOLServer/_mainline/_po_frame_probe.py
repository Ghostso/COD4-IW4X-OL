# -*- coding: utf-8 -*-
"""
_po_frame_probe.py - who owns the 'Live_Frame' / 'popup_connecting' page.

The '[100]...' panel is a Tenio component. Its descriptor neighbourhood in
.rdata contains, in this order:

    @PLATFORM_POPUP_CONNECTION    0x00AD28CC
    <during startup>              0x00AD28E8
    popup_connecting              0x00AD28FC
    Live_Frame                    0x00AD2910
    1750..1765 / 3290..3292 / 1741..1743   (already ASCII decimal ids!)
    popup_invite, menu_resetstats_warning, menu_cac_assault, ...

Because the numeric ids are stored as ASCII decimal strings, the loader
that consumes this block must be a text/config parser. This script hunts
for (a) the same block in the runtime dump, (b) a dword table of the
string addresses so the loader can index it, and (c) the '[%s] %s'
formatter neighbourhood in the dump.
"""
import os
import struct
import sys

import capstone

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
EXE = os.path.join(ROOT, "COD OL", "codoMP_client_shipRetail.exe")
RUNS = os.path.join(ROOT, "run_codol_001", "runs")
DUMP = os.path.join(RUNS, r"ENGINE_DUMP_20260925_114204\engine\engine_best.bin")
IMAGE_BASE = 0x00994000
RVA_BASE = 0x594000
MODULE_BASE = 0x00400000
MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)


def load(p):
    with open(p, "rb") as fh:
        return fh.read()


def find_all(b, n):
    out, s = [], 0
    while True:
        i = b.find(n, s)
        if i < 0:
            return out
        out.append(i)
        s = i + 1


def title(t):
    print("")
    print("=" * 78)
    print(t)
    print("=" * 78)


def a_pointer_table():
    title("A  is there a dword table of the provider strings? (disk + dump)")
    exe = load(EXE)
    dump = load(DUMP)
    names = [b"@PLATFORM_POPUP_CONNECTION", b"<during startup>",
             b"popup_connecting", b"Live_Frame", b"popup_invite"]
    for nm in names:
        dpos = exe.find(nm)
        d_va = MODULE_BASE + dpos
        gpos = dump.find(nm)
        g_va = IMAGE_BASE + gpos if gpos >= 0 else -1
        print("  %-28s disk VA 0x%08X   dump VA 0x%08X" % (
            nm.decode(), d_va, g_va))
        if gpos >= 0:
            pat = struct.pack("<I", g_va)
            refs = find_all(dump, pat)
            print("      dump refs to dump VA: %d  %s" % (
                len(refs), " ".join("dump+0x%X" % r for r in refs[:8])))
        pat = struct.pack("<I", d_va)
        refs = find_all(dump, pat)
        print("      dump refs to disk VA: %d" % len(refs))


def b_formatter_region():
    title("B  the formatter region around '[%s] %s' (disk 0x6CC764)")
    exe = load(EXE)
    lo, hi = 0x6CC740, 0x6CC9D0
    for row in range(lo, hi, 16):
        chunk = exe[row:row + 16]
        hexs = " ".join("%02X" % b for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print("   %06X  %-47s  %s" % (row, hexs, asc))


def c_dump_live_frame_context():
    title("C  Live_Frame neighbourhood in the runtime dump")
    dump = load(DUMP)
    pos = dump.find(b"Live_Frame")
    if pos < 0:
        print("  not in dump -> UNKNOWN")
        return
    lo = max(0, pos - 0x40)
    hi = min(len(dump), pos + 0x100)
    for row in range(lo, hi, 16):
        chunk = dump[row:row + 16]
        hexs = " ".join("%02X" % b for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print("   %08X  %-47s  %s" % (IMAGE_BASE + row, hexs, asc))


def d_search_loader_hints():
    title("D  loader hints: which module reads that block")
    exe = load(EXE)
    for nm in (b"TDR", b"tdr", b"Component", b"component", b"Creator",
               b"Popup", b"popup", b"ShowPopup", b"Live_Frame", b"SF_UI"):
        hits = find_all(exe, nm)
        print("  %-12s hits %d  %s" % (
            nm.decode(), len(hits),
            " ".join("0x%06X" % h for h in hits[:6])))
    # the '[%s] %s' at 0x63648C is inside the packed code; check its section
    print("")
    print("  note: 0x63648C and 0x6CC764 both live below RVA 0x594000?")
    print("    section for file 0x63648C : RVA 0x%06X" % 0x63648C)
    print("    section for file 0x6CC764 : RVA 0x%06X" % 0x6CC764)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "a"):
        a_pointer_table()
    if which in ("all", "b"):
        b_formatter_region()
    if which in ("all", "c"):
        c_dump_live_frame_context()
    if which in ("all", "d"):
        d_search_loader_hints()
