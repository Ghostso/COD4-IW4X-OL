from capstone import *
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
base=0x400000
off=0x7EF1E8-base
print("==== VA 0x007EF1E8 .. 0x007EF2F0 ====")
for ins in md.disasm(d[off:off+0x110], 0x7EF1E8):
    print("  %08X  %-20s %s %s"%(ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
print()
print("=== 相关字符串（从 dump 读）===")
for va in (0x00DE0610, 0x00DE0640, 0x00DE0928, 0x00DE0938, 0x00DE08C8, 0x00DE05E8, 0x00DE05FC):
    o=va-base
    if 0<=o<len(d):
        e=d.find(b"\x00",o)
        print("  VA 0x%08X -> %r"%(va, d[o:e].decode("latin1")))
print()
print("=== 跳转表 @0x7EF424 (6项) 与 @0x7EF43C (10项) ===")
import struct
for tbl,n in ((0x7EF424,6),(0x7EF43C,10)):
    print("  table 0x%08X:"%tbl, [hex(struct.unpack_from("<I",d,tbl-base+i*4)[0]) for i in range(n)])
