from capstone import *
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'; d=open(p,'rb').read(); md=Cs(CS_ARCH_X86,CS_MODE_32)
# Locate all call sites to functions in AF0xxx (attachment text/parser cluster) and print surrounding code.
for lo,hi in [(0xaf0000,0xaf0100),(0xaf0800,0xaf1000),(0xaf2000,0xaf3000)]:
 print('\nREGION',hex(lo),hex(hi))
 for s in range(lo,hi,0x20):
  chunk=d[s-0x400000:s-0x400000+0x100]
  ins=list(md.disasm(chunk,s))
  if any(i.mnemonic=='call' and i.op_str.startswith('0x') for i in ins):
   for i in ins: print(f'{i.address:08x} {i.mnemonic:<8} {i.op_str}')
   break
