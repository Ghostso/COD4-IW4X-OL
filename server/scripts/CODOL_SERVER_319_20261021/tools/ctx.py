from capstone import *
p = "D:/BaiduNetdiskDownload/使命召唤OL/run_codol_001/runs/OMIT_RETEST_20261022/mem/mem_005.bin"
d = open(p, "rb").read(); B = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
for a in (0x6618D1, 0x662BEF, 0x877CFB, 0x793F44, 0x794085, 0x793F55, 0x792987):
    print("=== ref 0x%08X ===" % a)
    start = a - 0x60
    for x in md.disasm(d[start-B:a-B+0x40], start):
        mark = " <<<" if x.address == a else ""
        print("  %08X  %-22s %s%s" % (x.address, x.bytes.hex(), x.mnemonic + " " + x.op_str, mark))
    print()