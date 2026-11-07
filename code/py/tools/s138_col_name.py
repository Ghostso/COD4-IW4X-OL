import struct,sys,re
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
E=r"E:\codol_re\client_image_20261027.bin";VA=0x400000
d=open(E,"rb").read();N=len(d)
def rd(va):
    o=va-VA
    return struct.unpack_from("<I",d,o)[0] if 0<=o<=N-4 else None
def cstr(va,ml=200):
    o=va-VA
    if not(0<=o<N):return None
    e=d.find(b"\x00",o)
    return d[o:e if 0<=e-o<=ml else o+ml].decode("latin1","replace")
# COL layout x86: +0 sig(1),+4 offset,+8 cdOff,+0xC pTD
for col in [0xB9A9B0]:
    print(hex(col),[hex(rd(col+i) or 0) for i in range(0,0x18,4)])
    tdi=rd(col+0xC); print("TD",hex(tdi or 0), cstr((tdi or 0)+8) if tdi else None)
# also scan backwards for COL with same pTD
