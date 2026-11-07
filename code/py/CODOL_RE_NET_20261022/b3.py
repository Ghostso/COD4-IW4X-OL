from capstone import *
d = open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin", "rb").read()
B = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
for va, n in [(0x4F3760, 0x100), (0x4F36C0, 0xC0)]:
    o = va - B
    start = None
    for k in range(0x200):
        if d[o-k] == 0x55 and d[o-k+1] == 0x8B and d[o-k+2] == 0xEC:
            start = B + o - k
            break
    s = start if start else va
    print("=====", hex(va), "start", hex(s))
    for ins in md.disasm(d[s-B:s-B+n], s):
        print(hex(ins.address), ins.mnemonic, ins.op_str)
