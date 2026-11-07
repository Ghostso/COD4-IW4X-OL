# -*- coding: utf-8 -*-
"""Phase B: relationship between 0x87C110 and 0x87D5A0; string->code association. Read-only."""
import sys, os, io, struct, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
b=C._bi; out=[]
def emit(s): out.append(s)

# Does 0x87D5A0 flow into 0x87D5A0's own code, or does 0x87C110 jump/call into 0x87D5A0's body?
emit("=== calls/jumps inside 0x87C110..0x87D593 targeting >=0x87D5A0 ===")
for k in C.idis_range(0x87C110, 0x87D593):
    if k.mnemonic in ("call","jmp") :
        t=C.target_of(k)
        if t is not None and t-C.IBI>=0x87D5A0:
            emit("  %08x %-8s %s -> %08x"%(k.address-C.IBI,k.mnemonic,k.op_str,t-C.IBI))

emit("")
emit("=== cross-calls 0x87C110 .. 0x87D593 -> inside 0x87C110 start (internal helpers?) ===")
# any call to 0x87D5A0 from anywhere in image
def callers(t):
    tv=C.IBI+t; rr=[]; i=0x1000
    while i<0x8a8000-5:
        if b[i]==0xE8:
            rel=struct.unpack("<i",b[i+1:i+5])[0]
            if (C.IBI+i)+5+rel==tv: rr.append(i)
        i+=1
    return rr
for t in (0x87C110,0x87D5A0,0x87A890,0x87AA40,0x87BE00):
    emit("  callers of %08x : %s"%(t,[hex(x) for x in callers(t)]))

# string -> code refs (correct RVA mapping)
emit("")
emit("=== net-buffer diagnostic strings: refs in code section ===")
strs=[(0x99EE98,"net-buffer NOT enough (real_len)"),
      (0x99EEF0,"string length error"),
      (0x99EF50,"wstring length error"),
      (0x99EFB8,"net-buffer NOT enough (unit_size/count)"),
      (0x99F290,"string from net-buffer format error"),
      (0x99F428,"wstring from net-buffer format error")]
code=C._bi[0x1000:0x8a8000]
for rva,label in strs:
    va=C.IBI+rva; pat=struct.pack("<I",va); refs=[]; i=0
    while True:
        j=code.find(pat,i)
        if j<0: break
        refs.append(0x1000+j); i=j+1
    emit("  %08x %-38s refs=%s"%(rva,label,[hex(x) for x in refs]))
io.open(os.path.join(C.EV,"dis_deser_rel_and_strings.txt"),"w",encoding="utf-8",newline="").write("\n".join(out)+"\n")
print("\n".join(out))
