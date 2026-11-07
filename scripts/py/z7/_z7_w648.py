import re, struct
img = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
d = open(img,"rb").read()
# C7 80-87 48 06 00 00 imm32 = mov [reg+0x648], imm32
pat1 = rb"\xc7[\x80-\x87]\x48\x06\x00\x00(....)"
# 89 80-BF 48 06 00 00 = mov [reg+0x648], reg32
pat2 = rb"\x89[\x80-\xbf]\x48\x06\x00\x00"
print("=== mov [reg+0x648], imm32 ===")
for m in re.finditer(pat1, d, re.S):
    va = BASE + m.start()
    imm = struct.unpack("<I", m.group(1))[0]
    print("0x%08X  mov [reg+0x648], 0x%08X (%d)" % (va, imm, imm))
print("=== mov [reg+0x648], reg32 ===")
for m in re.finditer(pat2, d, re.S):
    va = BASE + m.start()
    print("0x%08X  %s" % (va, d[m.start():m.start()+6].hex(" ")))
