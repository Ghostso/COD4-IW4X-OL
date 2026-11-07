# -*- coding: utf-8 -*-
"""Probe whether the packed .tp3 code section contains valid x86 at rest."""
import math

import capstone
import pefile

EXE = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"

with open(EXE, "rb") as fh:
    blob = fh.read()
pe = pefile.PE(EXE, fast_load=True)
ib = pe.OPTIONAL_HEADER.ImageBase
secs = list(pe.sections)
ep = pe.OPTIONAL_HEADER.AddressOfEntryPoint
pe.close()


def rva_to_off(rva):
    for s in secs:
        if s.VirtualAddress <= rva < s.VirtualAddress + s.Misc_VirtualSize:
            if s.PointerToRawData <= 0 or s.SizeOfRawData == 0:
                return None, s
            return s.PointerToRawData + (rva - s.VirtualAddress), s
    return None, None


def entropy(buf):
    counts = [0] * 256
    for b in buf:
        counts[b] += 1
    n = len(buf)
    e = 0.0
    for c in counts:
        if c:
            p = c / n
            e -= p * math.log2(p)
    return e


md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)


def disasm_at(rva, n=24):
    off, s = rva_to_off(rva)
    print("RVA 0x%08X VA 0x%08X section=%s off=%s" % (
        rva, ib + rva, s.Name.rstrip(b"\x00").decode("latin-1") if s else "?",
        hex(off) if off is not None else None))
    if off is None:
        return
    count = 0
    for insn in md.disasm(blob[off:off + 96], ib + rva):
        print("   0x%08X  %-24s %s" % (insn.address, insn.bytes.hex(), insn.mnemonic + " " + insn.op_str))
        count += 1
        if count >= n:
            break
    if count == 0:
        print("   (no valid instructions)")


print("=== entry point ===")
disasm_at(ep, 16)

print()
print("=== section 0 sample offsets ===")
s0 = secs[0]
SAMPLES = [0x1000, 0x10000, 0x100000, 0x200000, 0x300000, 0x400000, 0x500000]
for delta in SAMPLES:
    rva = s0.VirtualAddress + delta
    off, _ = rva_to_off(rva)
    if off is None or off >= len(blob):
        continue
    print("RVA 0x%08X off 0x%08X page-entropy %.3f" % (rva, off, entropy(blob[off:off + 0x1000])))
    disasm_at(rva, 6)
    print()

print("=== per-64KB entropy profile of section 0 (0x%X virtual) ===" % s0.Misc_VirtualSize)
for delta in range(0, s0.Misc_VirtualSize, 0x10000):
    rva = s0.VirtualAddress + delta
    off, _ = rva_to_off(rva)
    if off is None or off + 0x1000 > len(blob):
        break
    e = entropy(blob[off:off + 0x1000])
    bar = "#" * int(e * 3)
    print("  +0x%07X  RVA 0x%08X  %.3f %s" % (delta, rva, e, bar))
