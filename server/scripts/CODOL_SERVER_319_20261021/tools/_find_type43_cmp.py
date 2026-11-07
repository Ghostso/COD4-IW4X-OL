from capstone import *
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read(); md=Cs(CS_ARCH_X86,CS_MODE_32)
hits=[]
for s,e in [(0x401000,0xca7000),(0xca8000,0xe16000)]:
    off=s-0x400000
    insns=list(md.disasm(d[off:e-0x400000],s))
    for i,ins in enumerate(insns):
        op=ins.op_str.replace(' ','')
        if ('0x2b' in op or '43' in op) and ins.mnemonic in ('cmp','sub') and any(r in op for r in ['eax','ecx','edx','ebx','esi','edi','ebp']):
            ctx='; '.join(f'{x.mnemonic} {x.op_str}' for x in insns[max(0,i-3):min(len(insns),i+7)])
            hits.append((ins.address,ins.mnemonic,ins.op_str,ctx))
print('hits',len(hits))
for h in hits[:300]: print(f'{h[0]:08x} {h[1]} {h[2]} :: {h[3]}')
