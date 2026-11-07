"""
AUTHORITATIVE server writer model, derived instruction-by-instruction from:
  0x99590 MSG_WriteBits (incl. growth block 0x9960A)
  0x9949B MSG_WriteData
  0x99651 WriteLenStr
  0xA0400 WriteIndexDelta
  0xA0468 _CODOL2697_WriteConfigstrings
KEY RULE (0x9960A-0x99635): whenever bitpos%8==0 the writer RESYNCS bitpos = used*8,
then used++ and appends a zero byte. MSG_WriteData advances `used` and copies raw
bytes, WITHOUT touching bitpos -> the next byte-boundary resync JUMPS bitpos past them.
So A1 strings are interleaved as RAW BYTES and the bit fields skip over them.
"""
class Msg:
    def __init__(s):
        s.buf=bytearray(); s.used=0; s.bitpos=0
        s.log=[]
    def wbits(s,val,n,tag=""):
        for i in range(n):
            if s.bitpos % 8 == 0:
                s.bitpos = s.used*8      # <-- resync (0x9961F..0x99626)
                s.used += 1              # <-- 0x9962B..0x9962E
                s.buf.append(0)          # <-- 0x99631
            s.buf[s.bitpos>>3] |= ((val>>i)&1) << (s.bitpos & 7)
            s.bitpos += 1
        if tag: s.log.append((tag,s.bitpos,s.used))
    def wbyte(s,v,tag=""): s.wbits(v,8,tag)
    def wdata(s,data,tag=""):
        s.buf += data; s.used += len(data)
        if tag: s.log.append((tag,s.bitpos,s.used))
def idx(m,last,new):
    if new==last+1: m.wbits(1,1)
    else: m.wbits(0,1); m.wbits(new,13)
    return new

def build(a1,a2,a3,count1bits=16):
    m=Msg()
    m.wbyte(0x04,"after 0x04")
    m.wbits(len(a1) if a1 else 0,count1bits,"after count1")
    last=-1
    for i,s in a1:
        last=idx(m,last,i); m.wbits(last if False else 0,0) if False else None
        m.wdata(s.encode()+b"\0","after A1 str %r"%s)
    m.wbits(len(a2),10,"after A2 count")
    last=-1
    for i,v in a2:
        last=idx(m,last,i); m.wbits(v,10)
    m.wbits(len(a3),10,"after A3 count")
    last=-1
    for i,fa,fb,ex in a3:
        last=idx(m,last,i); m.wbits(fa,10); m.wbits(fb,7); m.wbits(len(ex),4)
        for e in ex: m.wbits(e,12)
    p06=m.bitpos
    m.wbyte(0x06,"after 0x06")
    return m,p06

cases=[("A1=[]",[],[],[]),
       ("A1=[(0,'')]",[(0,'')],[],[]),
       ("A1=[(0,'a')]",[(0,'a')],[],[]),
       ("A1=[(0,'a')] A2=[(0,1)]",[(0,'a')],[(0,1)],[]),
       ("A1=[(0,'a')] A2=[(0,1),(1,2)] A3=[(0,1023,127,[4095,1])]",[(0,'a')],[(0,1),(1,2)],[(0,1023,127,[4095,1])])]
print("%-58s %-12s %-12s" % ("case","bitpos@0x06","used(bytes)"))
for name,a1,a2,a3 in cases:
    m,p=build(a1,a2,a3)
    print("%-58s %-12d %-12d  buf=%s" % (name,p,m.used,m.buf.hex(' ')))
print()
print("=== trace of 'A1=[(0,'a')] A2=[(0,1)]' ===")
m,p=build([(0,'a')],[(0,1)],[])
for tag,bp,us in m.log: print("   %-22s bitpos=%-4d used=%d" % (tag,bp,us))
print("   -> terminating 0x06 starts at bitpos=%d ; used(before)=%d ; total bytes=%d" % (p, m.used-1 if m.used else 0, m.used))