import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\EARLIEST_20261027_123806'
LO = 0x00010000
img = open(os.path.join(D,'snap_002.bin'),'rb').read()
cov = open(os.path.join(D,'snap_002_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
def covok(i,n=4): return all(cov[i+k]==1 for k in range(n))
# 0x63E510 分配后调用 0x4f77f0 和 0x63bcb0。看 0x4f77f0 是构造什么
print('=== 0x4F77F0 函数开头 ===')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md=Cs(CS_ARCH_X86, CS_MODE_32)
c=rd(0x004F77F0,0x40)
if c:
    for ins in md.disasm(c,0x004F77F0):
        print('   %08X  %-16s %-7s %s' % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
        if ins.mnemonic=='ret': break
print()
# 关键: [0x82E1518] 为 0 说明没创建. 但 [0x82E1514] 也是 0.
# 0x63E5D6 mov [0x82e1514], ecx  <- ecx=[ebp+0xc] 参数
print('=== 0x63E510 的 [ebp+8] / [ebp+0xc] / [ebp+0x10] 分别被用于 ===')
for ins in md.disasm(rd(0x0063E510,0x100), 0x0063E510):
    if 'ebp + 8]' in ins.op_str or 'ebp + 0xc]' in ins.op_str or 'ebp + 0x10]' in ins.op_str:
        print('   %08X  %-16s %s' % (ins.address,ins.bytes.hex(),ins.op_str))
print()
print('=== 全局槽 0x082E1514 的所有写入点 ===')
pat=struct.pack('<I',0x082E1514)
i=img.find(pat,0)
while i>=0:
    if covok(i):
        va=LO+i
        if 0x400000<=va<0x0EA59000:
            print('   0x%08X  前4字节=%s' % (va, img[max(0,i-4):i].hex(' ')))
    i=img.find(pat,i+1)
