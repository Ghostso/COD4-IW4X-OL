d = open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin", "rb").read()
B = 0x400000
o = 0x614DA4 - B
b = d[o:o+21]
print("byte table len", len(b))
print("hex:", b.hex())
print("dec:", list(b))
o2 = 0x614D94 - B
import struct
print("dword table:", [hex(x) for x in struct.unpack_from("<4I", d[o2:o2+16])])
