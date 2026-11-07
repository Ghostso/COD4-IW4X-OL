from capstone import *
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read()
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
for va in [0x4EC400,0x5AD300,0x5ADD30,0x4F8D40,0x473A20,0x671140]:
 off=va-0x400000
 print(f'\n===== {va:08x} =====')
 for ins in md.disasm(d[off:off+0x300],va):
  print(f'{ins.address:08x}  {ins.bytes.hex():<20} {ins.mnemonic:<8} {ins.op_str}')
