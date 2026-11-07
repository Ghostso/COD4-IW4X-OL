import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
p=r'D:/BaiduNetdiskDownload/使命召唤OL/run_codol_001/runs/OMIT_RETEST_20261022/mem/mem_005.bin'
d=open(p,'rb').read(); base=0x400000
s=int(sys.argv[1],0); e=int(sys.argv[2],0)
md=Cs(CS_ARCH_X86,CS_MODE_32)
for i in md.disasm(d[s-base:e-base],s):
    print('%08X  %-18s %s'%(i.address,i.bytes.hex(),i.mnemonic+' '+i.op_str))
