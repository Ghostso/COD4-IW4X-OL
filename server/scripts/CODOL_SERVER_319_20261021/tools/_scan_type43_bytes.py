from capstone import *
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read(); md=Cs(CS_ARCH_X86,CS_MODE_32)
patterns=[bytes.fromhex(x) for x in ['83f82b','83f92b','83fa2b','83fb2b','83fe2b','83ff2b','3d2b000000','81f92b000000','81fa2b000000','81fb2b000000']]
hits=[]
for off in range(0x1000,0xa79000):
    for pat in patterns:
        if d.startswith(pat,off):
            va=off+0x400000
            insns=list(md.disasm(d[off-16:off+32],va-16))
            hits.append((va,pat.hex(),'; '.join(f'{x.address:08x}:{x.mnemonic} {x.op_str}' for x in insns)))
            break
print('hits',len(hits))
for h in hits: print(h[0],h[1],h[2])
