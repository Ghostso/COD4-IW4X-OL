"""Locate the /auth/ request builder that actually ran (auth_task == 10).
ASCII only.
"""
import re
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMG = (r"CODOLServer\_mainline\_dyn100_run_20260925_182324"
       r"\live\image_best.bin")
d = open(IMG, "rb").read()
base = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)


def refs(val):
    pat = re.compile(re.escape(val.to_bytes(4, "little")))
    return [base + m.start() for m in pat.finditer(d)]


print("=== refs to 0xD5A228 (\"auth_task\") ===")
for va in refs(0xD5A228):
    print("  0x%08X" % va)

print()
print("=== refs to 0xD5A114 (\"iv_seed\") ===")
for va in refs(0xD5A114):
    print("  0x%08X" % va)

print()
print("=== refs to 0xD59AEC (\"extra_data\") ===")
for va in refs(0xD59AEC):
    print("  0x%08X" % va)

print()
print("=== refs to 0xD5A0E8 (\"lsg_server_ticket\") ===")
for va in refs(0xD5A0E8):
    print("  0x%08X" % va)

print()
print("=== refs to 0xD5A31C (\"server_ticket\") ===")
for va in refs(0xD5A31C):
    print("  0x%08X" % va)

print()
print("=== refs to 0xD5A32C (\"client_ticket\") ===")
for va in refs(0xD5A32C):
    print("  0x%08X" % va)


def dis(va, n):
    print("---- 0x%08X .. (+0x%X) ----" % (va, n))
    for ins in md.disasm(d[va - base:va - base + n], va):
        print("  %08X  %-20s %s %s"
              % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))


for site in refs(0xD5A228):
    dis(site - 0x40, 0xA0)
