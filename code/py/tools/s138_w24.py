#!/usr/bin/env python3
"""s138_w24: 找写入 [obj+0x24] 的指令 (mov [r+0x24], imm/reg), 全 .text."""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000
TL, TH = 0x401000 - VA, 0x401000 + 0x8a689a - VA

MODRM_REG = set(range(0x40, 0x50)) | set(range(0x80, 0x90))  # mod=01/10 with various reg

print("=== 'mov dword ptr [reg+0x24], reg' 89 /r, modrm=0x4x (mod=01 disp8) ===")
hits = []
for i in range(TL, min(TH, N - 4)):
    if d[i] == 0x89 and d[i + 2] == 0x24 and 0x40 <= d[i + 1] <= 0x7F:
        # modrm mod=01 => disp8 follows, but here disp would be 0x24 -> so reg field varies, rm=4? Actually [reg+0x24] with mod=01 requires rm!=4
        pass
# simpler: use capstone on the region function 0xB83C00..0xB84200 and list writes
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md = Cs(CS_ARCH_X86, CS_MODE_32)
start = 0xB83A00
end = 0xB84500
for ins in md.disasm(d[start - VA:end - VA], start):
    if "+ 0x24]" in ins.op_str and ins.mnemonic.startswith("mov"):
        print("  0x%08X  %-30s %s" % (ins.address, ins.mnemonic + " " + ins.op_str, ""))
    if "+ 0x24]" in ins.op_str:
        print("  0x%08X  %-30s %s" % (ins.address, ins.mnemonic + " " + ins.op_str, ""))
