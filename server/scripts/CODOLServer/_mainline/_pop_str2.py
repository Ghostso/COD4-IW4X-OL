from capstone import *
import struct
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
def s(va, n=64):
    o=va-base
    if o<0 or o>=len(d): return "<out of dump>"
    e=d.find(b"\x00",o)
    return d[o:e].decode("latin1","replace")
for va in (0xDE08D8, 0xDE08C8, 0xDE0610, 0xDE0624, 0xDE0640, 0xDE0768, 0xDE0928, 0xDE0938, 0xDAE091):
    print("VA 0x%08X -> %r"%(va, s(va)))
print()
print("=== dwLogonStart 附近全串 (0xDE08A0..0xDE0960) ===")
o=0xDE08A0-base
seg=d[o:o+0x120]; i=0
while i<len(seg):
    j=i
    while j<len(seg) and 32<=seg[j]<127: j+=1
    if j-i>=3:
        print("   VA 0x%08X  %r"%(0xDE08A0+i, seg[i:j].decode("latin1"))); i=j
    else: i+=1
