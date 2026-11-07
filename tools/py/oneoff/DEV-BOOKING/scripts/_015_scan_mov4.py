# -*- coding: utf-8 -*-
"""015: byte-pattern scan for `mov dword ptr [reg+4], reg/imm` (disp8 form)."""
import struct
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD, cstr, dis  # noqa

lo = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x401000
hi = int(sys.argv[2], 16) if len(sys.argv) > 2 else END

hits = []
for i in range(lo - BASE, min(hi - BASE, len(DATA)) - 3):
    b0 = DATA[i]
    if b0 not in (0x89, 0xC7, 0x8B, 0x8D):
        continue
    modrm = DATA[i + 1]
    if (modrm >> 6) != 1:           # mod=01 (disp8)
        continue
    if (modrm & 7) == 4:            # SIB
        continue
    if DATA[i + 2] != 0x04:
        continue
    hits.append(BASE + i)

print("total pattern hits 0x%08X..0x%08X = %d" % (lo, hi, len(hits)))
for va in hits:
    st = va
    code = DATA[st - BASE: st - BASE + 20]
    ins = next(MD.disasm(code, st), None)
    if not ins:
        continue
    print("0x%08X  %-20s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
