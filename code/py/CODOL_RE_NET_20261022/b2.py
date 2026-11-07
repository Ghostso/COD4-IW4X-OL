from capstone import *
d = open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin", "rb").read()
B = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
va = 0x528470
o = va - B
start = None
for k in range(0x400):
    if d[o-k] == 0x55 and d[o-k+1] == 0x8B and d[o-k+2] == 0xEC:
        start = B + o - k
        break
print("func start", hex(start) if start else None)
va = start if start else va
for ins in md.disasm(d[va-B:va-B+0x180], va):
    print(hex(ins.address), ins.mnemonic, ins.op_str)
