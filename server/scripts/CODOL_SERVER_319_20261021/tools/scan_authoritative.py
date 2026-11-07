import struct
from capstone import *
p = "D:/BaiduNetdiskDownload/使命召唤OL/run_codol_001/runs/OMIT_RETEST_20261022/mem/mem_005.bin"
d = open(p, "rb").read(); B = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
DELTA = {0x670FF0:"ReadDeltaStruct", 0x670D30:"ReadDeltaField", 0x6701D0:"ReadDeltaField2",
         0x677E10:"WriteDeltaStruct", 0x6779B0:"WriteDeltaStruct2", 0x677D40:"LastChanged"}
calls = []
i = 0
while i < len(d) - 5:
    if d[i] == 0xE8:
        rel = struct.unpack_from("<i", d, i+1)[0]
        t = (i + B + 5 + rel) & 0xFFFFFFFF
        if t in DELTA:
            calls.append((i + B, t))
        i += 5
    else:
        i += 1
print("delta call sites:", len(calls))
prologues = []
i = 0
while i < len(d) - 4:
    if d[i] == 0x55 and d[i+1] == 0x8B and d[i+2] == 0xEC:
        prologues.append(i + B)
    i += 1
prologues.sort()
def func_of(va):
    lo = 0; hi = len(prologues) - 1; best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if prologues[mid] <= va:
            best = prologues[mid]; lo = mid + 1
        else:
            hi = mid - 1
    return best
funcs = {}
for va, t in calls:
    f = func_of(va)
    funcs.setdefault(f, set()).add(t)
print()
for f in sorted(funcs):
    print("  0x%08X -> %s" % (f, [DELTA[t] for t in sorted(funcs[f])]))
print()
alltabs = set()
for f in sorted(funcs):
    nxt = [p for p in prologues if p > f]
    end = nxt[0] if nxt else f + 0x2000
    if end - f > 0x4000: end = f + 0x4000
    tabs = set()
    for x in md.disasm(d[f-B:end-B], f):
        raw = x.bytes
        for k in range(len(raw) - 3):
            v = struct.unpack_from("<I", raw, k)[0]
            if 0xDA0000 <= v < 0xDB0000:
                tabs.add(v)
    if tabs:
        print("  0x%08X (len 0x%X): %s" % (f, end-f, " ".join("%08X" % t for t in sorted(tabs))))
        alltabs |= tabs
print()
print("UNION:", len(alltabs))
for t in sorted(alltabs):
    print("   0x%08X" % t)