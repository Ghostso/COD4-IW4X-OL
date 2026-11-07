# -*- coding: utf-8 -*-
"""
_s1_dump_xref.py - xref analysis against the runtime image dump of the CODOL
client.

Mapping derivation:
  module preferred base    = 0x00400000
  module was mapped at 0x00400000 in this run; dump base VA = 0x00994000
  dump offset 0x0          <=> runtime VA 0x00994000 <=> RVA 0x594000
  => dump_off = RVA - 0x594000 ; VA = 0x00994000 + dump_off
  Validation: '@SF_UI_DW_LIVE_CONNECTING_FAILED' file off 0x6CC640 sits in
              section 1 (RVA 0x8A8000, raw 0x594000) => RVA 0x9E0640
              => predicted dump off 0x44C640; observed 0x44C640. Exact match.
  Note the dump covers only RVA 0x594000..0xA65000, i.e. the second half of
  the code section plus all of .rdata. Code that lives below RVA 0x594000 is
  not in this dump.

This script therefore treats dump offsets directly as RVAs of a 0x4D1000-byte
image based at 0x00994000, disassembles around string references and resolves
call targets. Note the dump contains only the pages that were resident, so a
few regions are zero-filled.
"""
import os
import struct
import sys

import capstone

RUNS = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs"

DUMP_CANDIDATES = [
    os.path.join(RUNS, r"ENGINE_DUMP_20260925_114204\engine\engine_best.bin"),
    os.path.join(RUNS, r"ENGINE_DUMP_20260925_112143\engine\engine_best.bin"),
]

IMAGE_BASE = 0x00994000
IMAGE_SIZE = 0x4D1000

MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
MD.detail = True


def load():
    for p in DUMP_CANDIDATES:
        if os.path.exists(p):
            with open(p, "rb") as fh:
                return p, fh.read()
    raise SystemExit("no dump found")


def find_all(blob, needle):
    out = []
    s = 0
    while True:
        i = blob.find(needle, s)
        if i < 0:
            break
        out.append(i)
        s = i + 1
    return out


def scan_code_refs(blob, va):
    """Find 4-byte LE VA occurrences in the code range of the dump."""
    pat = struct.pack("<I", va)
    return find_all(blob, pat)


def disasm_around(blob, off, back=64, fwd=128, label=""):
    print("  --- disasm around dump+0x%X (VA 0x%08X) %s ---" % (off, IMAGE_BASE + off, label))
    lo = max(0, off - back)
    hi = min(len(blob), off + fwd)
    for insn in MD.disasm(blob[lo:hi], IMAGE_BASE + lo):
        mark = ""
        if insn.address == IMAGE_BASE + off:
            mark = "   <== HERE"
        print("     0x%08X  %-20s %s%s" % (
            insn.address, insn.bytes.hex(), insn.mnemonic + " " + insn.op_str, mark))


def main():
    path, blob = load()
    print("dump", path, "size 0x%X; image base 0x%08X" % (len(blob), IMAGE_BASE))

    anchors = [
        "@SF_UI_DW_LIVE_CONNECTING_FAILED",
        "@SF_UI_DW_LIVE_DISCONNECTED",
        "@SF_UI_DW_LIVE_CERT_FAILED",
        "DW_LOBBY_CONNECTED",
        "DW_LOBBY_ERROR",
        "dwLogonStart",
        "BD_LOBBY_PROTOCOL_VERSION_FAILURE",
        "BD_LOBBY_INTERNAL_FAILURE",
        "BD_MAX_ERROR_CODE",
        "Unknown bdLobbyErrorCode",
        "cppOnDWConnected",
        "cppOnDWDisconnected",
        "title_id",
        "tencent_ticket",
        "onlinegame",
    ]

    for a in anchors:
        positions = find_all(blob, a.encode("ascii"))
        if not positions:
            print("=" * 78)
            print("ANCHOR %s : NOT PRESENT IN DUMP" % a)
            continue
        for pos in positions:
            va = IMAGE_BASE + pos
            print("=" * 78)
            print("ANCHOR %-36s dump+0x%06X VA=0x%08X" % (a, pos, va))
            refs = scan_code_refs(blob, va)
            # a string VA can legitimately show up as data too; report everything
            print("  raw 4-byte LE references to this VA: %d" % len(refs))
            for r in refs[:8]:
                disasm_around(blob, r, back=48, fwd=96)


if __name__ == "__main__":
    main()
