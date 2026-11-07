import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
D = r'run_codol_001\runs\EARLIEST_20261027_123806'
LO = 0x00010000
img = open(os.path.join(D,'snap_002.bin'),'rb').read()
cov = open(os.path.join(D,'snap_002_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
md=Cs(CS_ARCH_X86, CS_MODE_32)
c=rd(0x0063E5EA,0x40)
print('=== 0x63E5EA 之后 (创建 dwRoomMatchUber) ===')
for ins in md.disasm(c,0x0063E5EA):
    print('  %08X  %-20s %-7s %s' % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
    if ins.address>0x0063E620: break
print()
print('=== 关键全局 0x082E1514 (存 dwRoomMatchUber 指针?) ===')
b=rd(0x082E1514,4)
print('  实测 [0x082E1514] = %s' % (('0x%08X'%struct.unpack('<I',b)[0]) if b else '未覆盖'))
