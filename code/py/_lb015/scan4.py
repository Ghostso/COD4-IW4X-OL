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

def align(va):
    for off in (2,1,3,4,5):
        st = va - off
        ins = mem.M.dis(st, count=1)
        if ins and ins[0].address <= va < ins[0].address + ins[0].size and ("0x82e13fc" in ins[0].op_str):
            return st, ins[0]
    return None, None

pat4 = re.compile(r"\[e[a-z0-9]+ \+ 4\]")
n_ok = 0
for va in hits:
    st, ins0 = align(va)
    if ins0 is None:
        print("UNALIGNED %08X" % va); continue
    n_ok += 1
    ins = mem.M.dis(st, count=16)
    m = [x for x in ins if pat4.search(x.op_str)]
    if m:
        print("==== %08X (owner ins %08X %s)" % (va, st, ins0.mnemonic+" "+ins0.op_str))
        for x in ins:
            print("   %08X %-18s %s" % (x.address, x.bytes.hex(), x.mnemonic+" "+x.op_str))
print("aligned ok:", n_ok)
