import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
idxs=[]
for line in open(os.path.join(D,'regions.txt'), encoding='utf-8', errors='replace'):
    if line.startswith('#'): continue
    p=line.split()
    if len(p)>=5: idxs.append((int(p[0],16), int(p[1],16), p[4]))
def cstr(va,n=72):
    for base,size,fn in idxs:
        if base <= va < base+size:
            f=open(os.path.join(D,fn),'rb').read()
            b=f[va-base:va-base+n]
            e=b.find(b'\x00')
            if e<1: return None
            t=b[:e].decode('latin1')
            return t if all(32<=ord(c)<127 for c in t) else None
    return None
def read_va(va,n):
    for base,size,fn in idxs:
        if base <= va < base+size:
            f=open(os.path.join(D,fn),'rb').read()
            return f[va-base:va-base+n]
    return None
md=Cs(CS_ARCH_X86, CS_MODE_32)
# 搜所有访问 [reg+0x10614] 的指令
print('=== 访问 [reg+0x10614] 的指令 ===')
import re
# 机器码 C6 8x / 80 8x / 8A 8x / 88 8x + modrm disp32
# 简化: 扫所有区域, 找 0x10614 作为 disp32 出现的位置
pat = struct.pack('<I', 0x00010614)
for base,size,fn in idxs:
    if not (0x400000 <= base < 0x0EA59000): continue
    try: dd=open(os.path.join(D,fn),'rb').read()
    except: continue
    i=dd.find(pat)
    while i>=0:
        va = base+i
        # disp32 在指令尾部, 指令起点 = va-3 附近
        for back in (3,4):
            s = va-back
            if s < 0: continue
            start = base+s
            code = dd[max(0,s-1):s+8]
            for ins in md.disasm(code, start):
                if 'wx10614' in ins.op_str.replace(' ','').replace('+','+') or '10614' in ins.op_str:
                    ann=''
                    if '0x' in ins.op_str:
                        for tok in ins.op_str.replace(',',' ').split():
                            if tok.startswith('0x'):
                                try: v=int(tok,16)
                                except: continue
                                if 0x00C00000<=v<=0x01000000:
                                    t=cstr(v)
                                    if t and len(t)>=4: ann='; "%s"'%t
                    print('   %08X  %-20s %-7s %-30s%s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, ann))
                break
        i=dd.find(pat, i+1)
