# -*- coding: utf-8 -*-
import os, capstone

p = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\Ayria\Plugins\CodolGameServer.Localnet32"

with open(p, "rb") as f:
    d = bytearray(f.read())

off = 0x209FAA
expected_orig = bytes.fromhex("81785000605d0e0f85c4100000e95b0b0000")
cur = d[off:off+len(expected_orig)]

print(f"Current bytes @ 0x{off:X}: {cur.hex()}")
assert bytes(cur) == expected_orig, "Mismatch at 0x209FAA!"

# Patch:
# 1. 0x0E5D6000 -> 0x0E659000 (00 90 65 0e)
# 2. 0f 85 c4 10 00 00 -> 90 90 90 90 90 90
patched = bytes.fromhex("8178500090650e" + "90"*6 + "e95b0b0000")
d[off:off+len(patched)] = patched

with open(p, "wb") as f:
    f.write(d)

print("[+] Successfully patched SizeOfImage check & bypassed jne failure at 0x209FAA!")

# Verify with capstone
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
for insn in md.disasm(d[off-10:off+25], 0x1020ABAA - 10):
    print("  0x%08X: %-10s %s" % (insn.address, insn.mnemonic, insn.op_str))