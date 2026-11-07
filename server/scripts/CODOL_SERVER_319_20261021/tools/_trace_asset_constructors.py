from capstone import *
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'; d=open(p,'rb').read(); md=Cs(CS_ARCH_X86,CS_MODE_32)
for va in [0x49c790,0x49c870,0x49cb60,0x49cc70,0x49dda0,0x49d760,0x49d8c0]:
 print('\n===',hex(va))
 for ins in md.disasm(d[va-0x400000:va-0x400000+0x260],va): print(f'{ins.address:08x} {ins.mnemonic:<8} {ins.op_str}')
