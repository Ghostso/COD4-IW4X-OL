from capstone import *
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'; d=open(p,'rb').read(); md=Cs(CS_ARCH_X86,CS_MODE_32)
for va in [0x483380,0x483390,0x4833a0,0x4833b0,0x4833c0,0x4833d0,0x4833e0,0x483400]:
 print('\n---',hex(va))
 off=va-0x400000
 for ins in md.disasm(d[off:off+0x40],va): print(f'{ins.address:08x} {ins.mnemonic:<8} {ins.op_str}')
