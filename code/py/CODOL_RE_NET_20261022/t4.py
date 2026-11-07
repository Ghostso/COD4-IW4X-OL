import struct
d = open(r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin","rb").read()
B = 0x400000
res = {}
for i in range(0x1000, 0x8A6890-6):
    if d[i] == 0xE8:
        rel = struct.unpack_from("<i", d, i+1)[0]
        t = (B+i+5+rel) & 0xffffffff
        if t in (0x670FF0, 0x6701D0, 0x670D30):
            ps = [struct.unpack_from("<I", d, j+1)[0] for j in range(max(0,i-30), i) if d[j] == 0x68]
            res.setdefault(t, []).append((B+i, ps))
out = []
for k, v in res.items():
    out.append("call 0x%X sites=%d" % (k, len(v)))
    for a, p in v:
        out.append("   %X pushes=%s" % (a, ",".join(hex(x) for x in p)))
print("\n".join(out))
