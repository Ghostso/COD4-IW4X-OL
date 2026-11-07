from capstone import *
d = open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin", "rb").read()
B = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
va = 0x5C0E40
for ins in md.disasm(d[va-B:va-B+0x1C0], va):
    print(hex(ins.address), ins.mnemonic, ins.op_str)
