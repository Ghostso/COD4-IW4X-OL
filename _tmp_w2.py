import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
idxs=[]
for line in open(os.path.join(D,'regions.txt'), encoding='utf-8', errors='replace'):
    if line.startswith('#'): continue
    p=line.split()
    if len(p)>=5: idxs.append((int(p[0],16), int(p[1],16), p[4]))
md=Cs(CS_ARCH_X86, CS_MODE_32)
md.detail=True
pat=struct.pack('<I', 0x00010614)
print('=== 全镜像搜 disp32 = 0x10614 ===')
n=0
for base,size,fn in idxs:
    if not (0x400000<=base<0x0EA59000): continue
    try: dd=open(os.path.join(D,fn),'rb').read()
    except: continue
    i=dd.find(pat)
    while i>=0 and n<40:
        va=base+i
        found=False
        for back in range(3,7):
            s=i-back
            if s<0: continue
            for ins in md.disasm(dd[s:i+4], base+s):
                if '10614' in ins.op_str and len(ins.bytes)==back+4:
                    print('   0x%08X  %-20s %-7s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
                    found=True; n+=1
                break
            if found: break
        i=dd.find(pat,i+1)
print('共', n)
