# -*- coding: utf-8 -*-
import sys, os, struct
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
# operand shapes inside 0x87D5A0 - look for bit-width immediates and buffer reads
import re
print("=== immediate operands in 0x87C110 and 0x87D5A0 (first 0x400 bytes each) ===")
for lo,hi,nm in [(0x87C110,0x87C200,"C110"),(0x87D5A0,0x87D6A0,"D5A0")]:
    cnt={}
    for ins in C.dis_range(lo,hi):
        m=re.search(r"0x([0-9a-f]+)", ins.op_str)
        if m and ins.mnemonic in ("shr","shl","and","movzx","mov","cmp","test","or"):
            v=int(m.group(1),16)
            if 1<=v<=32: cnt[v]=cnt.get(v,0)+1
    print(" ",nm,"small immediates:",dict(sorted(cnt.items())))
# callees of 0x87ED70
print()
print("0x87ED70 indirect call target slot VA 0xCA8330 ->", hex(struct.unpack_from("<I",C._img, 0xCA8330-0x400000+0)[0]) if C.in_file(0xCA8330-0x400000,4) else "n/a")
