import struct
from pathlib import Path
img=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
d=img.read_bytes(); BASE=0x400000
# look for a run of 0xCC (int3 padding) inside .text near 0xBA3xxx
def find_cc_runs(start, end, minlen=16):
    out=[]; i=start-BASE; n=0; run_start=None
    while i < end-BASE:
        if d[i]==0xCC:
            if run_start is None: run_start=i
            n+=1
        else:
            if n>=minlen: out.append((BASE+run_start, n))
            run_start=None; n=0
        i+=1
    if n>=minlen: out.append((BASE+run_start, n))
    return out
runs = find_cc_runs(0xBA3000, 0xBA5000, 16)
print("0xBA3000-0xBA5000 内的 0xCC 空隙（>=16 字节）：")
for va,n in runs[:20]:
    print("   0x%08X  len=%d" % (va,n))
print("total", len(runs))
