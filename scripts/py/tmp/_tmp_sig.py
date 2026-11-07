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
print('=== 注册函数 0x770890 开头 (bool) ===')
c=rd(0x770890,0x40)
for ins in md.disasm(c,0x770890):
    print('  %08X  %-16s %-7s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
    if ins.mnemonic=='ret': break
print()
print('=== 注册函数 0x770940 开头 (int) ===')
c=rd(0x770940,0x40)
for ins in md.disasm(c,0x770940):
    print('  %08X  %-16s %-7s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
    if ins.mnemonic=='ret': break
print()
print('=== 0x00DAE091 是什么字符串 ===')
b=rd(0x00DAE091, 40)
print('  ', b.hex(' ') if b else '未覆盖')
print('  ->', repr(b.split(b'\x00')[0].decode('latin1')) if b else '')
