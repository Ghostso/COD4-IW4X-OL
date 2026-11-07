# -*- coding: utf-8 -*-
"""
_po_ui_origin.py - static origin analysis for the in-game panel
"[100]failed to connect to lobby service" (@SF_UI_DW_LIVE_CONNECTING_FAILED).

Pure disk / existing-dump analysis. Launches nothing, injects nothing.

Datasets:
  DISK  : COD OL\\codoMP_client_shipRetail.exe  (TP3-packed; .rdata is plain,
          code is encrypted => file-offset xrefs are meaningless for code)
  DUMP  : run_codol_001\\runs\\ENGINE_DUMP_*\\engine\\engine_best.bin
          mapping: dump_off = RVA - 0x594000, VA = 0x00994000 + dump_off

It answers three things:
  1. every local placeholder key that lives adjacent to
     @SF_UI_DW_LIVE_CONNECTING_FAILED (the other error pages of the SAME UI page)
  2. whether the dump contains any pointer/ID table that indexes those keys,
     i.e. whether the page is selected by ID or by direct string pointer
  3. where the small integers around bdLobbyErrorCode / BD_MAX_ERROR_CODE /
     "Unknown bdLobbyErrorCode" live and whether 100 can be produced there
"""
import os
import struct
import sys

import capstone

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
EXE = os.path.join(ROOT, "COD OL", "codoMP_client_shipRetail.exe")
RUNS = os.path.join(ROOT, "run_codol_001", "runs")

DUMP_CANDIDATES = [
    os.path.join(RUNS, r"ENGINE_DUMP_20260925_114204\engine\engine_best.bin"),
    os.path.join(RUNS, r"ENGINE_DUMP_20260925_112143\engine\engine_best.bin"),
]

IMAGE_BASE = 0x00994000
RVA_BASE = 0x594000
MODULE_BASE = 0x00400000

MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
MD.detail = True


def load(path):
    with open(path, "rb") as fh:
        return fh.read()


def load_dump():
    for p in DUMP_CANDIDATES:
        if os.path.exists(p):
            return p, load(p)
    raise SystemExit("no runtime dump found")


def find_all(blob, needle):
    out = []
    s = 0
    while True:
        i = blob.find(needle, s)
        if i < 0:
            return out
        out.append(i)
        s = i + 1


def dump_off_to_va(off):
    return IMAGE_BASE + off


def dump_off_to_rva(off):
    return RVA_BASE + off


def report_section(title):
    print("")
    print("=" * 78)
    print(title)
    print("=" * 78)


def part1_localization_cluster():
    report_section("PART 1  placeholder keys near @SF_UI_DW_LIVE_CONNECTING_FAILED (localization.txt)")
    loc = os.path.join(ROOT, "COD OL", "localization.txt")
    blob = load(loc)
    # collect every @SF_UI_* / WIN_* key with its offset and Chinese text (GBK)
    keys = []
    for m in find_all(blob, b"@SF_"):
        end = blob.find(b"\n", m)
        if end < 0:
            continue
        keys.append((m, blob[m:end].strip().decode("ascii", "replace")))
    for m in find_all(blob, b"WIN_"):
        end = blob.find(b"\n", m)
        if end < 0:
            continue
        keys.append((m, blob[m:end].strip().decode("ascii", "replace")))
    keys.sort()
    print("localization.txt size 0x%X, keys found %d" % (len(blob), len(keys)))
    for off, name in keys:
        # the GBK string follows the key line, usually after a blank line
        tail = blob[off:off + 400]
        q1 = tail.find(b'"')
        q2 = tail.find(b'"', q1 + 1)
        text = ""
        if q1 >= 0 and q2 > q1:
            text = tail[q1 + 1:q2].decode("gbk", "replace")
        print("  0x%04X  %-40s %s" % (off, name, text.replace("\n", "\\n")))

    exe = load(EXE)
    report_section("PART 1b  same keys inside the EXE (.rdata style), file offset / VA")
    targets = [
        b"@SF_UI_DW_LIVE_CONNECTING_FAILED",
        b"@SF_UI_DW_LIVE_DISCONNECTED",
        b"@SF_UI_DW_LIVE_CERT_FAILED",
        b"WIN_IIPS_INIT_ERROR",
        b"WIN_NO_TCLS",
        b"WIN_ERROR",
    ]
    for t in targets:
        for pos in find_all(exe, t):
            print("  %-40s file 0x%06X  VA 0x%08X" % (t.decode(), pos, MODULE_BASE + pos))


def part2_string_tables_in_dump():
    report_section("PART 2  id/pointer tables for the SAME UI page, inside the runtime dump")
    path, blob = load_dump()
    print("dump %s  size 0x%X  base VA 0x%08X" % (path, len(blob), IMAGE_BASE))

    key = b"@SF_UI_DW_LIVE_CONNECTING_FAILED"
    pos = blob.find(key)
    if pos < 0:
        print("  key not present in dump -> UNKNOWN")
        return
    va = dump_off_to_va(pos)
    print("  key dump+0x%06X  VA 0x%08X" % (pos, va))

    lo = max(0, pos - 0x600)
    hi = min(len(blob), pos + 0x600)
    window = blob[lo:hi]
    print("  --- hex window around the key (dump+0x%X .. 0x%X) ---" % (lo, hi))
    for row in range(0, len(window), 16):
        chunk = window[row:row + 16]
        hexs = " ".join("%02X" % b for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print("   %08X  %-47s  %s" % (dump_off_to_va(lo + row), hexs, asc))

    # Do any 'push imm32' / 'mov reg, imm32' point at these keys?
    report_section("PART 2b  4-byte LE references to each @SF_UI_DW_LIVE_* key (dump-wide)")
    for name in (b"@SF_UI_DW_LIVE_CONNECTING_FAILED",
                 b"@SF_UI_DW_LIVE_DISCONNECTED",
                 b"@SF_UI_DW_LIVE_CERT_FAILED"):
        for p in find_all(blob, name):
            v = dump_off_to_va(p)
            pat = struct.pack("<I", v)
            refs = find_all(blob, pat)
            print("  %-34s VA 0x%08X  4-byte refs: %d" % (name.decode(), v, len(refs)))
            for r in refs[:10]:
                off = max(0, r - 24)
                line = []
                for insn in MD.disasm(blob[off:r + 32], dump_off_to_va(off)):
                    star = " <== push/mov" if insn.address == dump_off_to_va(r) else ""
                    line.append("      0x%08X  %s %s%s" % (
                        insn.address, insn.bytes.hex(), insn.mnemonic, insn.op_str + star))
                    if len(line) > 8:
                        break
                print("\n".join(line))

    # Look for a 4-byte table of VAs pointing into the .rdata key block.
    report_section("PART 2c  scan dump for a dense pointer table into the @SF_UI block")
    # The @SF_UI_* keys all sit in one .rdata neighbourhood; find the range.
    sf_positions = find_all(blob, b"@SF_UI_")
    if not sf_positions:
        print("  no @SF_UI_ keys in dump -> UNKNOWN")
        return
    lo_va = dump_off_to_va(min(sf_positions))
    hi_va = dump_off_to_va(max(sf_positions))
    print("  @SF_UI_ block VA 0x%08X .. 0x%08X  (%d keys)" % (lo_va, hi_va, len(sf_positions)))
    hits = []
    for i in range(0, len(blob) - 4, 4):
        v = struct.unpack_from("<I", blob, i)[0]
        if lo_va <= v <= hi_va + 0x60:
            hits.append((i, v))
    print("  dword-slot candidates pointing into the block: %d" % len(hits))
    # keep only runs of >=4 consecutive slots (i.e. real tables)
    runs = []
    cur = []
    for off, v in hits:
        if cur and off == cur[-1][0] + 4:
            cur.append((off, v))
        else:
            if len(cur) >= 4:
                runs.append(cur)
            cur = [(off, v)]
    if len(cur) >= 4:
        runs.append(cur)
    print("  consecutive runs of >=4: %d" % len(runs))
    for r in runs[:12]:
        base = r[0][0]
        print("    table dump+0x%06X VA 0x%08X  entries %d  RVA 0x%06X" % (
            base, dump_off_to_va(base), len(r), dump_off_to_rva(base)))
        for off, v in r[:8]:
            s_off = v - IMAGE_BASE
            s = blob[s_off:s_off + 48].split(b"\x00")[0].decode("ascii", "replace")
            print("        [%08X] -> 0x%08X  %s" % (off, v, s))


def part3_error_code_tables():
    report_section("PART 3  bdLobbyErrorCode enum table and the [100] number")
    exe = load(EXE)
    for name in (b"bdLobbyErrorCode", b"Unknown bdLobbyErrorCode", b"BD_MAX_ERROR_CODE"):
        for pos in find_all(exe, name):
            print("  %-26s file 0x%06X  VA 0x%08X" % (name.decode(), pos, MODULE_BASE + pos))

    # Structured-exception / enum metadata usually points at a name table.
    pos = exe.find(b"bdLobbyErrorCode")
    if pos < 0:
        print("  bdLobbyErrorCode not found -> UNKNOWN")
        return
    lo = max(0, pos - 0x400)
    hi = min(len(exe), pos + 0x400)
    print("")
    print("  --- hex window around bdLobbyErrorCode (file 0x%X .. 0x%X) ---" % (lo, hi))
    for row in range(lo, hi, 16):
        chunk = exe[row:row + 16]
        hexs = " ".join("%02X" % b for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print("   %06X  %-47s  %s" % (row, hexs, asc))

    # Count the small-int table that follows the BD_ name block.
    report_section("PART 3b  numeric table immediately before/after the BD_ name block")
    nums = []
    for i in range(lo, hi - 2):
        v = struct.unpack_from("<H", exe, i)[0]
        if 1 <= v <= 512:
            nums.append((i, v))
    print("  u16 values in 1..512 within window: %d" % len(nums))
    print("  first 40:")
    for off, v in nums[:40]:
        print("    0x%06X  %d" % (off, v))


def part4_summary():
    report_section("PART 4  what this dataset can and cannot answer")
    print("""
  ANSWERED (disk/dump evidence):
    * the panel text is a localization placeholder key, not a literal
    * the same UI page family is the @SF_UI_DW_LIVE_* block
    * the runtime dump that exists covers RVA >= 0x594000 only, so any code
      that lives in the packed region (RVA < 0x594000) is NOT observable
      statically. That is why direct xrefs to the key are absent.

  NOT ANSWERABLE from this dataset:
    * which function raises the panel, if it lives below RVA 0x594000
    * whether 100 is a Blaze code or a local index, unless the index table is
      inside the dumped .rdata (checked in PART 2/3)
""")


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "1"):
        part1_localization_cluster()
    if which in ("all", "2"):
        part2_string_tables_in_dump()
    if which in ("all", "3"):
        part3_error_code_tables()
    if which in ("all", "4"):
        part4_summary()


if __name__ == "__main__":
    main()
