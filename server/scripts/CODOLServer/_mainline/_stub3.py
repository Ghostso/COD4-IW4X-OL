from pathlib import Path
img=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
d=img.read_bytes(); BASE=0x400000
def runs(start,end,minlen):
    out=[]; i=start-BASE; n=0; rs=None
    while i<end-BASE:
        if d[i]==0xCC:
            if rs is None: rs=i
            n+=1
        else:
            if n>=minlen: out.append((BASE+rs,n))
            rs=None; n=0
        i+=1
    if n>=minlen: out.append((BASE+rs,n))
    return out
for lo,hi in [(0xBA3710,0xBA4400),(0xBA4400,0xBA6000),(0xB90000,0xBA0000)]:
    r=runs(lo,hi,12)
    print("%08X-%08X : %d 段" % (lo,hi,len(r)))
    for va,n in r[:6]: print("    0x%08X len=%d" % (va,n))
