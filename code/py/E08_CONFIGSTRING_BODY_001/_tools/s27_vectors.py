"""
Vector generator - matches the VERIFIED spec exactly (see 03_CONFIGSTRING_BODY_SPEC.md).
Everything here is CONSTRUCTED from instruction-level field rules, NOT from a captured frame.
=> These are CANDIDATE vectors, not Golden Vectors.
"""
class Msg:
    def __init__(s): s.b=bytearray(); s.bit=0
    def wbits(s,val,n):
        for i in range(n):
            if s.bit % 8 == 0: s.b.append(0)
            if (val>>i)&1: s.b[s.bit//8] |= 1<<(s.bit%8)   # LSB-first
            s.bit+=1
    def wbyte(s,v): s.wbits(v,8)

def put_index(m,last,new):
    """RVA 0xA0400: if new==last+1 -> bit 1 ; else bit 0 + 13-bit new. Returns new."""
    if new==last+1:
        m.wbits(1,1)
    else:
        m.wbits(0,1); m.wbits(new,13)
    return new

def idx_only(seq, start=-1):
    """Sub-vector: pure index-delta stream (100% VERIFIED rule)."""
    m=Msg(); last=start
    for v in seq: last=put_index(m,last,v)
    return m.b, m.bit

def a2_group(m, items, last=-1):
    m.wbits(len(items),10)                  # count2 : 10 bits  (VERIFIED)
    for idx,val in items:
        last=put_index(m,last,idx)
        m.wbits(val,10)                     # value : 10 bits  (VERIFIED)
    return last

def a3_group(m, recs, last=-1):
    m.wbits(len(recs),10)                   # count3 : 10 bits  (VERIFIED)
    for idx,fa,fb,extras in recs:
        last=put_index(m,last,idx)
        m.wbits(fa,10); m.wbits(fb,7); m.wbits(len(extras),4)
        for e in extras: m.wbits(e,12)
    return last

print("### SUB-VECTOR IDX-001 (index-delta only; rule 100% verified) ###")
for seq in ([0],[0,1],[0,1,2],[0,2],[5],[0,1,3,4]):
    b,bits=idx_only(seq)
    print("  seq=%-14s -> %-2d bits : %s" % (seq,bits,b.hex(" ")))
print()
print("### SUB-VECTOR A2-001 (10-bit count + {index,10-bit value}) ###")
for items in ([],[(0,0)],[(0,1),(1,2)],[(0,0x3FF)]):
    m=Msg(); a2_group(m,items)
    print("  items=%-24s -> %-3d bits : %s" % (items,m.bit,m.b.hex(" ")))
print()
print("### SUB-VECTOR A3-001 (10-bit count + {idx,10b,7b,4b n, n*12b}) ###")
for recs in ([],[(0,1,2,[])],[(0,0x3FF,0x7F,[0xFFF,0x001])]):
    m=Msg(); a3_group(m,recs)
    print("  recs=%-40s -> %-3d bits : %s" % (recs,m.bit,m.b.hex(" ")))
print()
print("### CANDIDATE FULL FRAME (count1 width is AMBIGUOUS -> two variants) ###")
def frame(count1_width):
    m=Msg(); m.wbyte(0x04)
    m.wbits(1,count1_width)                 # count1 (AMBIGUOUS: 8 or 16)
    # A1: index delta + (strlen+1) bytes
    last=put_index(m,-1,0)
    m.wbits(3,8); 
    for ch in b"hi\0": m.wbits(ch,8)
    # A2 empty, A3 empty
    m.wbits(0,10); m.wbits(0,10)
    m.wbyte(0x06)
    return m.b, m.bit
for wdt in (8,16):
    b,bits=frame(wdt)
    print("  count1=%2d bits -> %-3d bits : %s" % (wdt,bits,b.hex(" ")))