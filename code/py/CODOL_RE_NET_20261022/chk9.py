import struct
d = open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin", "rb").read()
B = 0x400000
base = 0x2FAFE10
vals = [struct.unpack("<I", d[base-B+i*4:base-B+i*4+4])[0] for i in range(0, 32)]
print(" | ".join(hex(v) for v in vals))
