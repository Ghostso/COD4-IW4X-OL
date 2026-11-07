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
hits.sort()
pat4 = re.compile(r"\[e[a-z0-9]+ \+ 4\]")
for va in hits:
    ins = mem.M.dis(va, count=14)
    # find index of the instruction that contains the immediate
    for idx,x in enumerate(ins):
        if "0x82e13fc" in x.op_str:
            break
    else:
        continue
    tail = ins[idx:idx+10]
    m = [x for x in tail if pat4.search(x.op_str)]
    if m:
        print("==== ref %08X" % va)
        for x in ins[:14]:
            print("   %08X %-18s %s" % (x.address, x.bytes.hex(), x.mnemonic+" "+x.op_str))
