# -*- coding: utf-8 -*-
"""
_pop3_static_scan.py - POP3 static pass over the strings/pointers that sit
around the in-game panel key @SF_UI_DW_LIVE_CONNECTING_FAILED.

Everything read here is read-only:
  * the shipped EXE               (COD OL\\codoMP_client_shipRetail.exe)
  * the engine runtime dump       (engine_best.bin, covers VA >= 0x00994000)

Mapping facts used (given, not re-derived):
    EXE file offset -> VA :  VA = file_offset + 0x714000
    engine dump off -> VA :  VA = 0x00994000 + off
    main module prefer base : 0x00400000

Outputs a plain text report on stdout.  No launch, no injection.
"""
import os
import struct
import sys

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
EXE = os.path.join(ROOT, "COD OL", "codoMP_client_shipRetail.exe")
DUMP = os.path.join(ROOT, "run_codol_001", "runs",
                    "ENGINE_DUMP_20260925_114204", "engine", "engine_best.bin")

EXE_TO_VA = 0x714000
DUMP_BASE = 0x00994000
IMG_BASE = 0x00400000

# Facts from the task brief / prior confirmed work.
PANEL_KEY_VA = 0x00DE0640      # @SF_UI_DW_LIVE_CONNECTING_FAILED
FORMAT_VA = 0x00DE0768         # '[%s] %s'

TARGETS = [
    ("panel key", 0x00DE0640),
    ("disconnected key", 0x00DBD888),
    ("cert failed key", 0x00DE09F0),
    ("[%s] %s formatter", 0x00DE0768),
    ("DW_LOBBY_ERROR", 0x00DE0990),
    ("DW_LOBBY_COMPLETE", 0x00DE0980),
    ("cppOnDWDisconnected", 0x00DE05E8),
    ("cppOnDWConnected", 0x00DE0600),
    ("MULTIPLE_LOGIN", 0x00DE05C0),
    ("LSG_DISCONNECT_IN_GAME", 0x00DE05D0),
    ("bdLobbyErrorCode", 0x00AD27F0),
    ("BD_MAX_ERROR_CODE", 0x00AD27D4),
]


def load(p):
    with open(p, "rb") as fh:
        return fh.read()


def find_all(blob, needle):
    out, s = [], 0
    while True:
        i = blob.find(needle, s)
        if i < 0:
            return out
        out.append(i)
        s = i + 1


def title(t):
    print("")
    print("=" * 78)
    print(t)
    print("=" * 78)


def hexwin(blob, va_lo, va_hi, base, label):
    """Dump [va_lo,va_hi) of a blob whose VA of offset 0 is `base`."""
    title(label)
    off = va_lo - base
    end = va_hi - base
    if off < 0 or end > len(blob):
        print("  range 0x%08X..0x%08X outside blob (0x%08X..0x%08X)"
              % (va_lo, va_hi, base, base + len(blob)))
        return
    for row in range(off & ~0xF, end, 16):
        chunk = blob[row:row + 16]
        hexs = " ".join("%02X" % b for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print("  0x%08X  %-47s  %s" % (base + row, hexs, asc))


def ascii_strings(blob, va_lo, va_hi, base, minlen=3):
    """Recover NUL-separated printable strings in a VA window."""
    off = max(0, va_lo - base)
    end = min(len(blob), va_hi - base)
    out = []
    i = off
    while i < end:
        j = i
        while j < end and 32 <= blob[j] < 127:
            j += 1
        if j - i >= minlen:
            out.append((base + i, blob[i:j].decode("ascii")))
        i = j + 1
    return out


def part1_disk_strings():
    title("PART 1  disk EXE: the .rdata block around the panel key (VA 0x00DE05B0..0x00DE0B60)")
    exe = load(EXE)
    # VA 0x00DE05B0 -> file offset VA-0x714000
    lo_va, hi_va = 0x00DE05B0, 0x00DE0B60
    hexwin(exe, lo_va, hi_va, EXE_TO_VA, "raw hex")
    print("")
    print("  --- printable strings in that window ---")
    for va, s in ascii_strings(exe, lo_va, hi_va, EXE_TO_VA, 3):
        print("   0x%08X  %s" % (va, s))


def part2_disk_tables():
    title("PART 2  disk EXE: 4-byte references to the panel key/formatter")
    exe = load(EXE)
    for name, va in ((("panel key"), PANEL_KEY_VA), ("formatter", FORMAT_VA)):
        pat = struct.pack("<I", va)
        hits = find_all(exe, pat)
        print("  %-12s VA 0x%08X -> file-offset hits %d  %s"
              % (name, va, len(hits),
                 " ".join("0x%06X(VA 0x%08X)" % (h, h + EXE_TO_VA)
                          for h in hits[:8])))


def part3_dump_pointers():
    title("PART 3  engine dump: every 4-byte word pointing into the .rdata key block")
    blob = load(DUMP)
    print("  dump %s size 0x%X base VA 0x%08X" % (DUMP, len(blob), DUMP_BASE))
    lo_va, hi_va = 0x00DB0000, 0x00DE2000
    table = []
    for i in range(0, len(blob) - 4):
        v = struct.unpack_from("<I", blob, i)[0]
        if lo_va <= v < hi_va:
            table.append((DUMP_BASE + i, v))
    print("  dword slots pointing into 0x%08X..0x%08X : %d" % (lo_va, hi_va, len(table)))
    # group into consecutive runs of 4+ entries
    runs, cur = [], []
    for va, v in table:
        if cur and va == cur[-1][0] + 4:
            cur.append((va, v))
        else:
            if len(cur) >= 4:
                runs.append(cur)
            cur = [(va, v)]
    if len(cur) >= 4:
        runs.append(cur)
    print("  consecutive runs >= 4 slots : %d" % len(runs))
    for r in runs:
        print("")
        print("   run at VA 0x%08X  entries %d" % (r[0][0], len(r)))
        for va, v in r[:24]:
            so = v - DUMP_BASE
            s = ""
            if 0 <= so < len(blob):
                s = blob[so:so + 48].split(b"\x00")[0].decode("ascii", "replace")
            print("      0x%08X -> 0x%08X  %r" % (va, v, s))


def part4_dump_targets():
    title("PART 4  engine dump: 4-byte references to each named target")
    blob = load(DUMP)
    for name, va in TARGETS:
        off = va - DUMP_BASE
        if not (0 <= off < len(blob)):
            print("  %-24s VA 0x%08X  (outside dump)" % (name, va))
            continue
        real = blob[off:off + 64].split(b"\x00")[0]
        pat = struct.pack("<I", va)
        hits = find_all(blob, pat)
        print("  %-24s VA 0x%08X  text=%-38r refs=%d %s"
              % (name, va, real.decode("ascii", "replace"), len(hits),
                 " ".join("0x%08X" % (DUMP_BASE + h) for h in hits[:6])))


def part5_bd_block():
    title("PART 5  disk EXE: BD_* enum name block boundaries")
    exe = load(EXE)
    for anchor in (b"BD_NO_ERROR", b"BD_MAX_ERROR_CODE",
                   b"BD_LOBBY_PROTOCOL_VERSION_FAILURE",
                   b"BD_LOBBIES_UNAVAILABLE", b"Unknown bdLobbyErrorCode"):
        hits = find_all(exe, anchor)
        for h in hits[:4]:
            print("  %-38s file 0x%06X VA 0x%08X"
                  % (anchor.decode(), h, h + EXE_TO_VA))


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "1"):
        part1_disk_strings()
    if which in ("all", "2"):
        part2_disk_tables()
    if which in ("all", "3"):
        part3_dump_pointers()
    if which in ("all", "4"):
        part4_dump_targets()
    if which in ("all", "5"):
        part5_bd_block()
