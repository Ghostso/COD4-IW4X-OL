import struct
p = "../../run_codol_001/runs/OMIT_RETEST_20261022/mem/mem_005.bin"
d = open(p, "rb").read()
B = 0x400000
def ok(o, b):
    return o <= 0x4000 and (b == 0 or 1 <= b <= 32 or -110 <= b <= -50)
runs = []
S = 0xDA0000
while S < 0xDB0000:
    o = S - B; n = 0
    while o + n*12 + 12 <= len(d):
        off, bits, pad = struct.unpack_from("<Iii", d, o + n*12)
        if not ok(off, bits): break
        n += 1
        if n > 600: break
    if n >= 4: runs.append((S, n))
    S += 4
m = []
for a, n in runs:
    if m and a < m[-1][0] + m[-1][1]*12: continue
    m.append((a, n))
print("candidates", len(m))
for a, n in m:
    pat = struct.pack("<I", a); hits = []; i = 0x401000 - B
    while True:
        i = d.find(pat, i, 0x8A8000 - B)
        if i < 0: break
        hits.append(i + B); i += 1
    if hits:
        print("0x%08X n=%-4d refs=%s" % (a, n, " ".join("%08X" % h for h in hits[:10])))