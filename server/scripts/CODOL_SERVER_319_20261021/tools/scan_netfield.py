import struct
p = r"D:/BaiduNetdiskDownload/使命召唤OL/run_codol_001/runs/OMIT_RETEST_20261022/mem/mem_005.bin"
d = open(p, "rb").read()
BASE = 0x400000

def plausible(off, bits):
    if off > 0x1000: return False
    if bits == 0: return True
    if 1 <= bits <= 32: return True
    if -110 <= bits <= -50: return True
    return False

runs = []
for start in range(0xDA0000, 0xDB0000, 4):
    o = start - BASE
    n = 0
    while True:
        if o + n*12 + 12 > len(d): break
        off, bits, pad = struct.unpack_from("<Iii", d, o + n*12)
        if not plausible(off, bits): break
        n += 1
        if n > 400: break
    if n >= 8:
        runs.append((start, n))

merged = []
for a, n in runs:
    if merged and a < merged[-1][0] + merged[-1][1]*12:
        continue
    merged.append((a, n))

print("candidate netField tables:")
for a, n in merged:
    print("  0x%08X  %3d entries" % (a, n))