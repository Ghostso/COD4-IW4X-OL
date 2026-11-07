from capstone import *
d=open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin","rb").read()
B=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32)
va=0x670FF0
o=va-B
s=0
for k in range(0x300):
    if d[o-k]==0x55 and d[o-k+1]==0x8B and d[o-k+2]==0xEC:
        s=va-k;break
out=["start 0x%X"%s]
for i in md.disasm(d[s-B:s-B+0x300],s): out.append("%X %s %s"%(i.address,i.mnemonic,i.op_str))
print(chr(10).join(out))