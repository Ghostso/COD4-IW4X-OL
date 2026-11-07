# -*- coding: utf-8 -*-
import struct
import fast, img, mem
from img import dword as IDW, read as IRD
M = mem.M
def hx(x): return "0x%X" % x
def show(a,n=0x40,label=""):
    print("--- %s %s ---"%(hx(a),label))
    ins = img.dis(a,n=n) if 0x401000<=a<0xE65000 else M.dis(a,n=n)
    cnt=0
    for i in ins:
        print("  %08X %-18s %s"%(i.address,i.bytes.hex(),i.mnemonic+" "+i.op_str)); cnt+=1
        if cnt>22: break
for a,l in ((0x730280,"net A"),(0x731440,"net B"),(0x730490,"net C"),(0x738E70,"listener1"),(0x738bf0,"l1a"),(0x738d00,"l1b"),(0x737430,"l1c")):
    show(a,label=l)

# scan image for call dword [0xCAxxxx]
IMG=img._IMG; BASE=img.BASE
slots={}
for i in range(len(IMG)-6):
    if IMG[i]==0xFF and IMG[i+1]==0x15:
        a=struct.unpack_from("<I",IMG,i+2)[0]
        if 0xCA7000<=a<=0xCB2000:
            slots.setdefault(a,[]).append(BASE+i)
print("distinct IAT slots used:", len(slots))
for a in sorted(slots):
    tgt = M.dword(a)
    print("  slot %s used@%s -> dump %s" % (hx(a), [hx(x) for x in slots[a][:3]], hx(tgt) if tgt else tgt))
