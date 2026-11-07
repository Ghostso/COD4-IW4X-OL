import struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
def hexdump(va,n):
    o=va-BASE
    print("--- %08X ---" % va)
    for r in range(0,n,16):
        chunk=d[o+r:o+r+16]
        print("%08X  %-47s  %s" % (va+r, " ".join("%02x"%b for b in chunk),
              "".join(chr(b) if 32<=b<127 else "." for b in chunk)))
for va in (0xDC73A0, 0xDC7840):
    hexdump(va, 0x60)
print()
# scan for [reg+0x288] writes  (c6 8? 88 02 00 00 01) and general +0x288 refs
print("=== instructions touching +0x288 ===")
import capstone
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail=True
found=[]
for i in range(len(d)-16):
    if d[i] in (0xC6,0xC7,0x80,0x81,0x83,0x84,0xF6,0xF7,0x88,0x89,0x8A,0x8B,0x0F):
        pass
# simpler: textual scan of disasm over the whole image is expensive; do targeted patterns
pats = [b"\xc6\x86\x88\x02\x00\x00\x01", b"\xc6\x85\x88\x02\x00\x00\x01", b"\xc6\x87\x88\x02\x00\x00\x01",
        b"\xc6\x80\x88\x02\x00\x00\x01", b"\xc6\x81\x88\x02\x00\x00\x01", b"\xc6\x82\x88\x02\x00\x00\x01",
        b"\xc6\x83\x88\x02\x00\x00\x01", b"\xc6\x84\x88\x02\x00\x00\x01"]
for p in pats:
    s=0
    while True:
        i=d.find(p,s)
        if i<0: break
        found.append((i+BASE,p.hex()))
        s=i+1
for va,p in found:
    print("%08X  %s" % (va,p))
print("total imm-writes of +0x288 = 1 pattern matches:",len(found))
