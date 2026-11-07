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
print('=== 函数 0x808650 的真正结尾 0x808920..0x808935 ===')
code=rd(0x00808920,0x18)
for ins in md.disasm(code,0x00808920):
    print('  %08X  %-20s %-7s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
print()
print('  解读: 0x808920 call 0x770890 (注册"1765") -> 0x808925 add esp,0x20')
print('        0x808928 pop esi / 0x80892E pop ebx / mov esp,ebp / pop ebp / ret')
print('  => 返回值 al = dvar注册函数(0x770890) 的返回，函数本身不显式设 al')
print()
print('=== 验证: 0x770890 的返回值语义 ===')
code=rd(0x770890,0xC0)
for ins in md.disasm(code,0x770890):
    if ins.mnemonic in ('mov','xor','or','test','je','jne','ret','setne','sete','cmp'):
        print('  %08X  %-20s %-7s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
    if ins.mnemonic=='ret': break
