import re, struct
img = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
d = open(img,"rb").read()
# mov dword [reg+0x240], imm  : C7 80/81/82/83/86/87 40020000 <imm32>
pats = [
    rb"\xc7[\x80-\x87]0\x02\x00\x00(....)",   # C7 80..87 disp32 imm32 (disp=0x240)
]
# more precise: C7 8x 40 02 00 00 imm32
pat = rb"\xc7[\x80-\x87]\x40\x02\x00\x00(....)"
print("=== writes to [reg+0x240] ===")
for m in re.finditer(pat, d, re.S):
    va = BASE + m.start()
    imm = struct.unpack("<I", m.group(1))[0]
    print("0x%08X  mov dword[reg+0x240], %d (0x%X)" % (va, imm, imm))
# also mov [reg+0x240], reg : 89 8x/9x 40020000
pat2 = rb"\x89[\x80-\xbf]\x40\x02\x00\x00"
print("=== mov [reg+0x240], reg32 ===")
for m in re.finditer(pat2, d, re.S):
    va = BASE + m.start()
    b = d[m.start():m.start()+6]
    print("0x%08X  %s" % (va, b.hex(" ")))
