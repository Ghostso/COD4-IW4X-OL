# -*- coding: utf-8 -*-
"""Base.dll RVA 映射 + 读资源表。"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DLL = os.path.join(os.path.dirname(ROOT), "run_codol_001",
                   "sandbox_datafix_20260929",
                   "codoMP_client_shipRetailBase.dll")
SEC = [(".text", 0x1000, 0x742000, 0x400),
       (".rdata", 0x743000, 0x26C000, 0x742000),
       (".data", 0x9AF000, 0x153000, 0x9AD200),
       (".idata2", 0xB02000, 0x4EBA, 0xAF7C00),
       (".rsrc2", 0xB07000, 0x2B9C, 0xAFCC00),
       (".tls", 0xB0A000, 0xED3000, 0xAFF800),
       (".tvm0", 0x19DD000, 0x1F5E000, 0x19D1E00),
       (".reloc", 0x393B000, 0x56000, 0x392F400)]


def rva2off(r):
    for nm, va, vs, rp in SEC:
        if va <= r < va + vs:
            return nm, rp + (r - va)
    return None, None


def main():
    b = open(DLL, "rb").read()
    print("dll bytes %d" % len(b))
    for t in (0x239B120, 0x1E2D338, 0xE5C8C0, 0x49D3B0, 0x4A9330):
        nm, off = rva2off(t)
        print("RVA 0x%08X -> %s off=%s" % (t, nm, hex(off) if off else None))
        if off:
            print("    %s" % b[off:off + 32].hex(" "))
    nm, off = rva2off(0x239B120)
    if off:
        print("== table rows stride 0x1C ==")
        for r in range(20):
            row = b[off + r * 0x1C:off + (r + 1) * 0x1C]
            if len(row) < 0x1C:
                break
            print("  [%2d] %s" % (r, " ".join("%08X" % v
                                               for v in struct.unpack("<7I", row))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
