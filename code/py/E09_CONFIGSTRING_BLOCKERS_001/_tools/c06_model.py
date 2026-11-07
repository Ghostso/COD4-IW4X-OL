"""Model the SERVER writer exactly as decompiled, to compute the 0x06 bit offset.
server: WriteByte(0x04)=WriteBits(8) ; WriteShort(count1)=8*2 bits ; then WriteIndexDelta (WriteBits) ;
        then WriteLenStr = MSG_WriteData(buf,str,len+1)  [BYTE-level: advances used, NOT bitpos] ;
        then WriteBits for A2/A3 ; finally WriteByte(0x06)=WriteBits(8)
KEY: MSG_WriteData does NOT update [msg+0x10] (bitpos). Verify consequence.
"""
class Msg:
    def __init__(s):
        s.buf=bytearray(); s.used=0   # [msg+4] byte count
        s.bitpos=0                    # [msg+0x10]
    # WriteBits semantics (verbatim from 0x99590 + growth block 0x9960A)
    def wbits(s,val,n):
        for i in range(n):
            if s.bitpos % 8 == 0:
                # growth: append zero byte, used++
                s.buf.append(0); s.used+=1
            byteidx = s.bitpos >> 3
            bit = (val >> i) & 1
            if byteidx < len(s.buf):
                s.buf[byteidx] |= bit << (s.bitpos & 7)
            s.bitpos += 1
    def wbyte(s,v): s.wbits(v,8)
    def wdata(s, data):
        # MSG_WriteData: copies at buf+used, then used += len ; bitpos UNCHANGED
        s.buf += data; s.used += len(data)

def idx(m,last,new):
    if new==last+1: m.wbits(1,1)
    else: m.wbits(0,1); m.wbits(new,13)
    return new

def build(a1):
    m=Msg(); m.wbyte(0x04); m.wbits(1,16)  # count1 = 1 (WriteShort)
    last=-1
    for i,s in a1:
        last=idx(m,last,i)
        m.wdata(s.encode()+b"\0")     # WriteLenStr -> MSG_WriteData (byte-level)
    m.wbits(0,10); m.wbits(0,10)      # A2 empty, A3 empty
    b06_start=m.bitpos
    m.wbyte(0x06)
    return m,b06_start

for a1 in ([],[(0,'')],[(0,'a')],[(0,'hello')]):
    m,p=build(a1)
    print("A1=%-18s  bitpos before 0x06=%-4d  used(bytes)=%-3d  buf=%s" % (a1,p,m.used,m.buf.hex(' ')))
print()
print("NOTE bitpos(%d) vs used*8(%d): %s" % (p, m.used*8, "MISMATCH -> WriteData did not advance bitpos" if p!=m.used*8 else "aligned"))