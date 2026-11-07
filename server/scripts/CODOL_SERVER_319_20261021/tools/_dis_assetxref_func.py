from capstone import *
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'; d=open(p,'rb').read(); md=Cs(CS_ARCH_X86,CS_MODE_32)
for s,e in [(0x49ca00,0x49cd80),(0x49d300,0x49d700)]:
 print('\n===',hex(s))
 for ins in md.disasm(d[s-0x400000:e-0x400000],s): print(f'{ins.address:08x} {ins.mnemonic:<8} {ins.op_str}')
