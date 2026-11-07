import re
img = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
d = open(img,"rb").read()
# 8B 85 74 F8 FF FF = mov eax,[ebp-0x774]; also 8B 8D / 8B 95 variants
pats = [
    rb"\x8b[\x85\x8d\x95\xbd\xb5]\x74\xf8\xff\xff",
]
print("=== readers of [ebp-0x774] ===")
for pat in pats:
    for m in re.finditer(pat, d, re.S):
        va = BASE + m.start()
        if 0x800000 <= va <= 0x810000:  # same function region
            print("0x%08X  %s" % (va, d[m.start():m.start()+6].hex(" ")))
