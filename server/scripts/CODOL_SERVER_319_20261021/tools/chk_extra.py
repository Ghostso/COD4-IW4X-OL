import struct
p = "D:/BaiduNetdiskDownload/使命召唤OL/run_codol_001/runs/OMIT_RETEST_20261022/mem/mem_005.bin"
d = open(p, "rb").read(); B = 0x400000
for a, label in [(0xDA8528,"0xDA8520+8"), (0xDA9330,"0xDA9330"), (0xDA9334,"0xDA9334"), (0xDA9920,"0xDA9920")]:
    o = a - B
    print("=== %s 0x%08X ===" % (label, a))
    for r in range(0, 48, 16):
        print("   %s" % " ".join("%02X" % b for b in d[o+r:o+r+16]))
    ents = [struct.unpack_from("<Iii", d, o+i*12) for i in range(4)]
    print("   as netField:", [(hex(e[0]), e[1]) for e in ents])
    print()