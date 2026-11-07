from capstone import *
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read(); md=Cs(CS_ARCH_X86,CS_MODE_32)
for va in [0x483410,0x483420,0x483470,0x4834b0,0x4834c0,0x4834d0,0x4834e0,0x891120]:
    print('\n---',hex(va))
    for ins in md.disasm(d[va-0x400000:va-0x400000+0x60],va):
        print(f'{ins.address:08x} {ins.mnemonic:<8} {ins.op_str}')
