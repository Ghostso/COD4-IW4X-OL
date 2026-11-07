"""Server writer semantics -> byte vectors (CONSTRUCTED from VERIFIED field rules)."""
import struct
class Msg:
    def __init__(s): s.b=bytearray(); s.bit=0
    def wbits(s,val,n):
        for i in range(n):
            if s.bit % 8 == 0: s.b.append(0)
            if (val>>i)&1: s.b[s.bit//8] |= 1<<(s.bit%8)   # LSB-first (verified)
            s.bit+=1
    def wbyte(s,v): s.wbits(v,8)
    def wshort(s,v): s.wbits(v,16)
    def wlong(s,v): s.wbits(v,32)
def putindex(m,cur,new):
    # from RVA 0xA0400: if cur+1==new: wbits(1,1)  else: wbits(0,1); wbits(new,13)
    if cur+1==new: m.wbits(1,1)
    else: m.wbits(0,1); m.wbits(new,13)
    return new
def body(m, a1, a2, a3):
    """a1: list[(idx,str)] ; a2: list[(idx,str)] ; a3: list of recs (see below)."""
    # A1: count (2 bits) then per-entry: index-delta + string bits(len+1, 8-bit units)
    m.wbits(len(a1),2)
    cur=-1
    for idx,s in a1:
        cur=putindex(m,cur,idx)
        m.wbits(len(s)+1,8)          # (strlen+1) written as 8-bit field
        for ch in s.encode():
            m.wbits(ch,8)
    # A2: count (11 bits) then per-entry: index-delta + (strlen+1) as 10-bit
    m.wbits(len(a2),11)
    cur=-1
    for idx,s in a2:
        cur=putindex(m,cur,idx)
        m.wbits(len(s)+1,10)
    # A3: count (10 bits) then per-record: index-delta, 10-bit v, 7-bit v, 4-bit n, n x 12-bit
    m.wbits(len(a3),10)
    cur=-1
    for (idx,f10,f7,extra) in a3:
        cur=putindex(m,cur,idx)
        m.wbits(f10,10); m.wbits(f7,7); m.wbits(len(extra),4)
        for e in extra: m.wbits(e,12)
    return bytes(m.b), m.bit
m=Msg()
m.wbyte(0x04); m.wshort(0x0001)
b,nb=body(m,[(0,"hi")],[],[])
m.wbyte(0x06)
print("VECTOR CS-001 (A1=[(0,'hi')], A2=[], A3=[]):")
print("  bits=%d  bytes=%s" % (nb, m.b.hex(" ")))
print()
m=Msg(); m.wbyte(0x04); m.wshort(0x0002)
b,nb=body(m,[(0,"a"),(5,"bb")],[],[])
m.wbyte(0x06)
print("VECTOR CS-002 (A1=[(0,'a'),(5,'bb')]):")
print("  bits=%d  bytes=%s" % (nb, m.b.hex(" ")))
print()
m=Msg(); m.wbyte(0x04); m.wshort(0x0000)
b,nb=body(m,[],[],[])
m.wbyte(0x06)
print("VECTOR CS-003 (empty sets):")
print("  bits=%d  bytes=%s" % (nb, m.b.hex(" ")))