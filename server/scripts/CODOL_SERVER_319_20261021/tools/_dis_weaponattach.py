from capstone import *
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'; d=open(p,'rb').read(); md=Cs(CS_ARCH_X86,CS_MODE_32)
for va in [0xe5c880,0xe5c8a0]:
 print('---',hex(va))
 for ins in md.disasm(d[va-0x400000:va-0x400000+0x100],va): print(f'{ins.address:08x} {ins.mnemonic:<8} {ins.op_str}')
