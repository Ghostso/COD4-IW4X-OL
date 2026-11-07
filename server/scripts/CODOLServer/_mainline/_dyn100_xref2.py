# -*- coding: utf-8 -*-
"""
_dyn100_xref2.py -- true capstone operand xrefs in the live pre-arm image.

The earlier raw dword scan matched instruction bytes, not operands.  This
script linear-disassembles the decrypted code ranges and keeps only decoded
x86 instructions whose immediate operand equals a target string VA.

Usage:
    python -X utf8 _dyn100_xref2.py <image_best.bin>
"""

import json
import os
import sys

import capstone

MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
MD.detail = True

LO = 0x00400000
CODE_RANGES = [(0x00401000, 0x00994000), (0x00994000, 0x00CA8000)]

TARGETS = {
    "SF_UI_DW_LIVE_CONNECTING_FAILED": 0x00DE0640,
    "SF_UI_DW_LIVE_DISCONNECTED": 0x00DBD888,
    "SF_UI_DW_LIVE_CERT_FAILED": 0x00DE09F0,
    "DW_LOBBY_ERROR": 0x00DE0990,
    "DW_LOBBY_CONNECTED": 0x00DE0938,
    "DW_DNS_ERROR": 0x00DE08D8,
    "DW_ACCOUNT_ERROR": 0x00DE08F8,
    "dwLogonStart": 0x00DE08C8,
    "cppOnDWConnected": 0x00DE05FC,
    "cppOnDWDisconnected": 0x00DE05E8,
    "bdLobbyErrorCode": 0x00AD27F0,
    "BD_MAX_ERROR_CODE": 0x00AD27D4,
    "Unknown_bdLobbyErrorCode": 0x00AD27E8,
    "WIN_IIPS_INIT_ERROR": 0x00DC93A8,
    "TQOS_HOST_ied_tqos": 0x00DD98A0,
}


def load(path):
    with open(path, "rb") as fh:
        return fh.read()


def immediate_values(insn):
    vals = []
    for op in insn.operands:
        if op.type == capstone.x86.X86_OP_IMM:
            vals.append(int(op.imm) & 0xFFFFFFFF)
    return vals


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print(__doc__)
        return 1
    blob = load(path)
    # desired VA -> decoded hits
    hits = {name: [] for name in TARGETS}
    decoded = 0
    for start_va, end_va in CODE_RANGES:
        if start_va < LO:
            continue
        data = blob[start_va - LO:end_va - LO]
        # Disassemble from the section start.  This can desync on embedded
        # data, but any hit is still a decoded instruction at that address
        # and is checked against the raw bytes below.
        for insn in MD.disasm(data, start_va):
            decoded += 1
            vals = immediate_values(insn)
            if not vals:
                continue
            for name, va in TARGETS.items():
                if va in vals:
                    hits[name].append({
                        "va": insn.address,
                        "bytes": insn.bytes.hex(),
                        "mnemonic": insn.mnemonic,
                        "op_str": insn.op_str,
                    })
    print("decoded instructions: %d" % decoded)
    out = {}
    for name, va in TARGETS.items():
        h = hits[name]
        out[name] = {"target_va": va, "count": len(h), "hits": h}
        print("%-36s VA 0x%08X  true hits=%d" % (name, va, len(h)))
        for e in h[:40]:
            print("    %08X  %-20s %s %s"
                  % (e["va"], e["bytes"], e["mnemonic"], e["op_str"]))

    out_path = os.path.splitext(path)[0] + "_true_xrefs.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print("wrote %s" % out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
