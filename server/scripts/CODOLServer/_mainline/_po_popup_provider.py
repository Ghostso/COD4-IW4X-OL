# -*- coding: utf-8 -*-
"""
_po_popup_provider.py - second pass on the [100] panel origin.

Findings to prove / probe:
  F1  The panel is NOT drawn by native game code that references the
      @SF_UI_DW_LIVE_* key. Next to that key in .rdata sits a Lua/provider
      name table:  '<during startup>' / 'popup_connecting' / 'Live_Frame'
      plus numeric component ids 1750..1765, 3290..3292, 1741..1743.
      => the page is a Tenio (Tencent UI framework) component addressed by
         NAME + numeric id, i.e. 'popup_connecting' on the 'Live_Frame'.

  F2  The '[%s] %s' format string lives at VA 0x00DE0768 right next to the
      keys, so the panel text is built by a printf-style formatter fed with
      (error token, localized string).

  F3  'Unknown bdLobbyErrorCode' / 'bdLobbyErrorCode' sit at .rdata
      0x6D27E4+. The MSVC enum-name table is a contiguous NUL-terminated
      string block, so the enum values can be recovered from the .rdata
      block that starts before BD_NO_ERROR.

This script only reads disk + the existing runtime dump.
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
MODULE_BASE = 0x00400000
IMAGE_BASE = 0x00994000
RVA_BASE = 0x594000
MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)


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


def f1_provider_block():
    title("F1  provider / component table next to the @SF_UI_DW_LIVE_* keys")
    exe = load(EXE)
    # strings that sit immediately after the UI keys in .rdata
    probes = [
        b"<during startup>",
        b"popup_connecting",
        b"Live_Frame",
        b"popup_invite",
        b"@PLATFORM_POPUP_CONNECTION",
        b"menu_resetstats_warning",
        b"[%s] %s",
        b"wargod",
    ]
    for p in probes:
        hits = find_all(exe, p)
        print("  %-28s hits %d %s" % (
            p.decode(), len(hits),
            " ".join("0x%06X(VA 0x%08X)" % (h, MODULE_BASE + h) for h in hits[:6])))

    # dump the numeric id run right after 'Live_Frame'
    pos = exe.find(b"Live_Frame")
    if pos >= 0:
        lo = max(0, pos - 0x20)
        hi = min(len(exe), pos + 0x120)
        print("")
        print("  --- numeric region after Live_Frame (file 0x%X) ---" % pos)
        for row in range(lo, hi, 16):
            chunk = exe[row:row + 16]
            hexs = " ".join("%02X" % b for b in chunk)
            asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            print("   %06X  %-47s  %s" % (row, hexs, asc))


def f1b_dump_provider():
    title("F1b same provider block inside the runtime dump + who swaps it in")
    for p in DUMP_CANDIDATES:
        if not os.path.exists(p):
            continue
        blob = load(p)
        print("  dump", p)
        for name in (b"popup_connecting", b"<during startup>", b"Live_Frame"):
            hits = find_all(blob, name)
            print("    %-18s hits %d %s" % (
                name.decode(), len(hits),
                " ".join("dump+0x%06X(VA 0x%08X)" % (h, IMAGE_BASE + h) for h in hits[:4])))
        # any 4-byte refs to the 'popup_connecting' string?
        for h in find_all(blob, b"popup_connecting"):
            va = IMAGE_BASE + h
            pat = struct.pack("<I", va)
            refs = find_all(blob, pat)
            print("    'popup_connecting' VA 0x%08X refs %d" % (va, len(refs)))
            for r in refs[:6]:
                off = max(0, r - 32)
                for insn in MD.disasm(blob[off:r + 32], IMAGE_BASE + off):
                    star = " <== HERE" if insn.address == IMAGE_BASE + r else ""
                    print("        0x%08X  %-14s %s %s%s" % (
                        insn.address, insn.bytes.hex(), insn.mnemonic, insn.op_str, star))
        break


def f2_format_string():
    title("F2  the '[%s] %s' formatter used for '[100]...' text")
    exe = load(EXE)
    pos = exe.find(b"[%s] %s")
    while pos >= 0:
        print("  '[%%s] %%s' file 0x%06X VA 0x%08X" % (pos, MODULE_BASE + pos))
        pos = exe.find(b"[%s] %s", pos + 1)
    # other bracket formats nearby
    for pat in (b"[%d]", b"%s %d", b"295 %s %d", b"297 %s %d"):
        hits = find_all(exe, pat)
        for h in hits:
            print("  %-12s file 0x%06X VA 0x%08X" % (pat.decode(), h, MODULE_BASE + h))


def f3_enum_block():
    title("F3  BD_* enum name block, recover order and look for index 100")
    exe = load(EXE)
    # Walk backwards from BD_MAX_ERROR_CODE collecting contiguous name-like
    # NUL-terminated tokens (the MSVC enum name table).
    anchor = exe.find(b"BD_MAX_ERROR_CODE")
    if anchor < 0:
        print("  anchor missing -> UNKNOWN")
        return
    print("  BD_MAX_ERROR_CODE file 0x%06X" % anchor)
    # find the start of the contiguous string block
    start = anchor
    while True:
        nxt = exe.rfind(b"\x00", 0, start - 1)
        if nxt < 0 or start - nxt > 0x120:
            break
        tok = exe[nxt + 1:start]
        if not tok or not all(32 <= c < 127 for c in tok):
            break
        start = nxt + 1
        if start < anchor - 0x12000:
            break
    end = anchor
    while True:
        nxt = exe.find(b"\x00", end + 1)
        if nxt < 0:
            break
        tok = exe[end + 1:nxt]
        if not tok or not all(32 <= c < 127 for c in tok):
            end = end + 1
            break
        end = nxt
        if end > anchor + 0x4000:
            break
    block = exe[start:end + 1]
    names = [t.decode("ascii") for t in block.split(b"\x00") if t]
    print("  contiguous enum-name block file 0x%06X..0x%06X  tokens %d" % (
        start, end, len(names)))
    for i, n in enumerate(names):
        mark = ""
        if i == 100:
            mark = "   <<<<<< index 100"
        if n.startswith("BD_") or mark or i < 4 or i > len(names) - 5:
            print("   [%3d] %s%s" % (i, n, mark))


def f4_min_requirements():
    title("F4  lobby host / dvar surface reachable from disk (context for D)")
    exe = load(EXE)
    for name in (b"onlinegame", b"lobbyhost", b"dwblazehost", b"blazehost",
                 b"dw_lobby", b"dw_session", b"title_id", b"tencent_ticket",
                 b"ied-tqos.qq.com", b"stun1-tub.codol.qq.com"):
        hits = find_all(exe, name)
        print("  %-24s hits %d %s" % (
            name.decode(), len(hits),
            " ".join("VA 0x%08X" % (MODULE_BASE + h) for h in hits[:4])))


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "1"):
        f1_provider_block()
        f1b_dump_provider()
    if which in ("all", "2"):
        f2_format_string()
    if which in ("all", "3"):
        f3_enum_block()
    if which in ("all", "4"):
        f4_min_requirements()
