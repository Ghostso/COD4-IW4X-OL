# -*- coding: utf-8 -*-
import mem, struct, re
K = 0x82E13FC
hits = []
for s, sz, data in mem.M.regions:
    pat = struct.pack("<I", K)
    i = data.find(pat)
    while i >= 0:
        hits.append(s + i)
        i = data.find(pat, i+1)
def scan_window(va, win=30):
    return mem.M.dis(va-12, count=win)
cnt = 0
for va in hits:
    ins = scan_window(va)
    found = [x for x in ins if re.search(r"\+\s*4\]", x.op_str)]
    if found:
        cnt += 1
        print("---- ref at %08X" % va)
        for x in ins:
            print("   %08X %-20s %s" % (x.address, x.bytes.hex(), x.mnemonic+" "+x.op_str))
print("refs with +4 mem operand:", cnt)
