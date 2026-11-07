# -*- coding: utf-8 -*-
"""
_dyn100_tbl.py -- hunt for the string-resolution mechanism of the lobby UI.

Hypotheses tested against the live full image:
  H1  pointer table: a dense run of 4-byte VAs pointing into the @SF_UI
      .rdata block (the UI page might be selected by index into this table)
  H2  ID table: `[100]` is an index into a name table near bdLobbyErrorCode
  H3  the code loads a base register then uses small offsets (common for
      packed images); report any `mov/lea reg, imm32` whose imm is close to
      a target but not equal

Usage:
    python -X utf8 _dyn100_tbl.py <image_best.bin>
"""

import json
import os
import struct
import sys

import capstone

MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
MD.detail = True

LO = 0x00400000
CODE_RANGES = [(0x00401000, 0x00994000), (0x00994000, 0x00CA8000)]

FOCUS = {
    "SF_UI_DW_LIVE_CONNECTING_FAILED": 0x00DE0640,
    "SF_UI_DW_LIVE_DISCONNECTED": 0x00DBD888,
    "SF_UI_DW_LIVE_CERT_FAILED": 0x00DE09F0,
    "dwLogonStart": 0x00DE08C8,
    "WIN_IIPS_INIT_ERROR": 0x00DC93A8,
}


def load(path):
    with open(path, "rb") as fh:
        return fh.read()


def find_all(blob, needle):
    out, s = [], 0
    while True:
        i = blob.find(needle, s)
        if i < 0:
            return out
        out.append(i)
        s = i + 1


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print(__doc__)
        return 1
    blob = load(path)
    print("image %s size 0x%X" % (path, len(blob)))

    print("")
    print("=" * 78)
    print("H1  pointer table into the @SF_UI .rdata block")
    print("=" * 78)
    pos = find_all(blob, b"@SF_UI_")
    print("@SF_UI_ key count: %d" % len(pos))
    if pos:
        lo_va = LO + min(pos)
        hi_va = LO + max(pos)
        print("block VA range 0x%08X .. 0x%08X" % (lo_va, hi_va))
        slots = []
        for i in range(0, len(blob) - 4, 4):
            v = struct.unpack_from("<I", blob, i)[0]
            if lo_va - 0x40 <= v <= hi_va + 0x40:
                slots.append((i, v))
        print("dword slots pointing into block: %d" % len(slots))
        runs, cur = [], []
        for off, v in slots:
            if cur and off == cur[-1][0] + 4:
                cur.append((off, v))
            else:
                if len(cur) >= 3:
                    runs.append(cur)
                cur = [(off, v)]
        if len(cur) >= 3:
            runs.append(cur)
        print("consecutive runs >=3: %d" % len(runs))
        for r in runs[:15]:
            base = r[0][0]
            print("  table VA 0x%08X entries=%d" % (LO + base, len(r)))
            for off, v in r[:10]:
                s_off = v - LO
                s = blob[s_off:s_off + 56].split(b"\x00")[0].decode("ascii", "replace")
                print("      [%08X] -> 0x%08X  %s" % (LO + off, v, s))

    print("")
    print("=" * 78)
    print("H2  small-int / ID tables around the BD_ block")
    print("=" * 78)
    for name in (b"bdLobbyErrorCode", b"Unknown bdLobbyErrorCode",
                 b"BD_MAX_ERROR_CODE", b"BD_LOBBY_PROTOCOL_VERSION_FAILURE"):
        for p in find_all(blob, name):
            print("  %-32s VA 0x%08X" % (name.decode(), LO + p))
    p = blob.find(b"bdLobbyErrorCode")
    if p >= 0:
        lo = max(0, p - 0x200)
        hi = min(len(blob), p + 0x200)
        print("  --- hexdump around it (VA 0x%08X ..) ---"
              % (LO + lo))
        for row in range(lo, hi, 16):
            chunk = blob[row:row + 16]
            h = " ".join("%02X" % b for b in chunk)
            a = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            print("   %08X  %-47s  %s" % (LO + row, h, a))

    print("")
    print("=" * 78)
    print("H3  near-immediate loads (base+offset addressing)")
    print("=" * 78)
    near = {k: [] for k in FOCUS}
    for start_va, end_va in CODE_RANGES:
        data = blob[start_va - LO:end_va - LO]
        for insn in MD.disasm(data, start_va):
            if insn.mnemonic not in ("mov", "lea", "push", "add", "sub"):
                continue
            for op in insn.operands:
                if op.type != capstone.x86.X86_OP_IMM:
                    continue
                imm = int(op.imm) & 0xFFFFFFFF
                for name, tva in FOCUS.items():
                    d = abs(imm - tva)
                    if 0 < d <= 0x2000:
                        near[name].append(
                            {"va": insn.address, "imm": imm, "delta": d,
                             "text": "%s %s" % (insn.mnemonic, insn.op_str)})
    for name, lst in near.items():
        print("%-36s near hits=%d" % (name, len(lst)))
        lst.sort(key=lambda e: e["delta"])
        for e in lst[:20]:
            print("    %08X  imm=0x%08X delta=0x%X  %s"
                  % (e["va"], e["imm"], e["delta"], e["text"]))

    out_path = os.path.splitext(path)[0] + "_tbl.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({"near": near, "sf_ui_count": len(pos)}, fh, indent=2)
    print("wrote %s" % out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
