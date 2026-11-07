from capstone import *
d=open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin","rb").read()
B=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32)
va=0x471760
out=[]
for i in md.disasm(d[va-B:va-B+0x180],va): out.append("%X %s %s"%(i.address,i.mnemonic,i.op_str))
print(chr(10).join(out))