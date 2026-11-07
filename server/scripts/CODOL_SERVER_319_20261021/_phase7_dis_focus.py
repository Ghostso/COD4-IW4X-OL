from capstone import *
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'; d=open(p,'rb').read(); md=Cs(CS_ARCH_X86,CS_MODE_32)
for s,n in [(0x4ec500,0x500),(0x4ebf00,0x600)]:
 print(f'\n=== {s:08x} ===')
 for ins in md.disasm(d[s-0x400000:s-0x400000+n],s): print(f'{ins.address:08x} {ins.mnemonic:<7} {ins.op_str}')
