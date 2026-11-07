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
# 找函数入口, 看 ebx 从哪来
print('=== 往前找序言 0x00808600..0x008087A0 ===')
code=rd(0x00808600,0x1A0)
if code:
    for ins in md.disasm(code,0x00808600):
        if ins.address>0x008087A0: break
        mark=' <<<' if ins.address in (0x008087A4,) else ''
        if ins.mnemonic in ('mov','xor','push','and','or','sub','add') and 'ebx' in ins.op_str:
            print('  %08X  %-20s %-7s %s%s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, mark))
