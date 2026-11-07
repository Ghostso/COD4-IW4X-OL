# -*- coding: utf-8 -*-
"""
_m8_fullimage_xrefs.py - find the code that raises the [100] panel in the
full-image runtime dump captured by suspend_host_redirect.py --full-image.

Dump mapping: image_best.bin offset 0 == VA 0x00400000.
Read-only.
"""
import os
import struct
import sys

import capstone

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
DEFAULT = os.path.join(ROOT, "CODOLServer", "_fullimage", "run2",
                       "fullimage", "image_best.bin")
BASE = 0x00400000

MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
MD.detail = True

ANCHORS = [
    b"@SF_UI_DW_LIVE_CONNECTING_FAILED",
    b"@SF_UI_DW_LIVE_DISCONNECTED",
    b"@SF_UI_DW_LIVE_CERT_FAILED",
    b"DW_LOBBY_CONNECTED",
    b"DW_LOBBY_ERROR",
    b"dwLogonStart",
    b"cppOnDWConnected",
    b"cppOnDWDisconnected",
    b"BD_LOBBY_PROTOCOL_VERSION_FAILURE",
    b"BD_LOBBY_INTERNAL_FAILURE",
    b"BD_MAX_ERROR_CODE",
    b"Unknown bdLobbyErrorCode",
    b"bdLobbyErrorCode",
    b"[%s] %s",
    b"WIN_IIPS_INIT_ERROR",
    b"WIN_NO_TCLS",
]


def find_all(blob, needle):
    out, s = [], 0
    while True:
        i = blob.find(needle, s)
        if i < 0:
            return out
        out.append(i)
        s = i + 1


def is_code_va(va):
    return 0x00401000 <= va < 0x00CA8000


def disasm_context(blob, va, back=64, forward=48):
    lo = max(BASE, va - back)
    hi = min(BASE + len(blob), va + forward)
    o = lo - BASE
    out = []
    for ins in MD.disasm(blob[o:o + (hi - lo)], lo):
        out.append("0x%08X  %-22s %s %s%s" % (
            ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str,
            "   <== REF" if ins.address == va else ""))
    return out


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    with open(path, "rb") as fh:
        blob = fh.read()
    print("image  %s" % path)
    print("size   %d (0x%X)   base VA 0x%08X" % (len(blob), len(blob), BASE))
    nz = sum(1 for b in blob if b)
    print("nonzero %d" % nz)

    print("")
    print("=== anchor strings ===")
    for a in ANCHORS:
        hits = find_all(blob, a)
        if not hits:
            print("  %-38s : none" % a.decode("latin1"))
            continue
        print("  %-38s : %d" % (a.decode("latin1"), len(hits)))
        for h in hits[:6]:
            print("      file 0x%06X  VA 0x%08X" % (h, BASE + h))

    print("")
    print("=== 4-byte code references to the panel key and lobby strings ===")
    for a in ANCHORS:
        hits = find_all(blob, a)
        for h in hits:
            sva = BASE + h
            pat = struct.pack("<I", sva)
            refs = find_all(blob, pat)
            code_refs = [r for r in refs if is_code_va(BASE + r)]
            if not refs:
                continue
            print("")
            print("ANCHOR %r  str VA 0x%08X  refs=%d code_refs=%d"
                  % (a[:48], sva, len(refs), len(code_refs)))
            for r in refs[:12]:
                rva = BASE + r
                tag = "CODE" if is_code_va(rva) else "data"
                print("   ref file 0x%06X  VA 0x%08X  (%s)" % (r, rva, tag))
                if is_code_va(rva):
                    for line in disasm_context(blob, rva):
                        print("      " + line)

    print("")
    print("=== any 4-byte refs to the '[%s] %s' formatter ===")
    for h in find_all(blob, b"[%s] %s"):
        sva = BASE + h
        refs = find_all(blob, struct.pack("<I", sva))
        print("  formatter VA 0x%08X  refs=%d" % (sva, len(refs)))
        for r in refs[:12]:
            rva = BASE + r
            print("     ref 0x%08X  [%s]" % (rva, "CODE" if is_code_va(rva) else "data"))


if __name__ == "__main__":
    main()
