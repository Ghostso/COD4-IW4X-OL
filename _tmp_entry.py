import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
idxs=[]
for line in open(os.path.join(D,'regions.txt'), encoding='utf-8', errors='replace'):
    if line.startswith('#'): continue
    p=line.split()
    if len(p)>=5: idxs.append((int(p[0],16), int(p[1],16), p[4]))
def read_va(va,n):
    for base,size,fn in idxs:
        if base <= va < base+size:
            f=open(os.path.join(D,fn),'rb').read()
            return f[va-base:va-base+n]
    return None
md=Cs(CS_ARCH_X86, CS_MODE_32)
print('=== 往前找函数序言: 0x0063C560..0x0063C770 ===')
code=read_va(0x0063C560, 0x210)
prev=None
for ins in md.disasm(code, 0x0063C560):
    if ins.address > 0x0063C770: break
    mark=''
    if ins.mnemonic in ('push','mov') and ins.address<0x0063C6A0:
        if ins.bytes.hex() in ('558bec','8bff558bec'):
            mark='  <<< 函数入口'
    print('  %08X  %-20s %-7s %-30s%s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, mark))
