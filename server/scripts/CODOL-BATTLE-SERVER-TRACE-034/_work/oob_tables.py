import capstone, struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def u32(va): return struct.unpack_from("<I",d,va-BASE)[0]
print("=== jump table A @0x5C0F2C (state-3..6 branch, from 0x5C0673) ===")
for i in range(4):
    t=u32(0x5C0F2C+i*4); print("   [%d] -> %08X" % (i,t))
print()
print("=== jump table B @0x5C0F3C (command 3..6 branch, from 0x5C0707) ===")
for i in range(4):
    t=u32(0x5C0F3C+i*4); print("   [%d] -> %08X" % (i,t))
print()
print("=== strings referenced by the OOB handler ===")
def s(va):
    o=va-BASE; e=d.find(b'\x00',o); return d[o:e]
for va in (0xDBC445,0xDCA06C,0xDAE091,0xDCDC0C,0xDA0CDC,0xDBB708,0xDE68E8,0xDC5694):
    try: print("   %08X : %r" % (va, s(va)[:70]))
    except Exception as e: print("   %08X : ERR %s" % (va,e))
